import asyncio
import logging
from typing import List, Dict, Any, Optional
from litellm import Router, completion_cost
from pydantic import BaseModel
import json
import threading

from .model_lists import chat_model_list
from .models import MDCResponse
from .tokenize_utils import get_tokenizer, tokenize
from .prompts import format_consolidation_prompt


# Configure litellm Router
router = Router(
    model_list=chat_model_list,
    num_retries=3,
    timeout=30,
    routing_strategy="least-busy",  # Use least-busy strategy for optimal throughput
    fallbacks=[],  # General fallbacks for any error
    context_window_fallbacks=[
        {"gpt-4o-mini": ["gemini-2.0-flash"]},
        {"gpt-4o": ["gemini-2.0-flash"]},
        {"deepseek-chat": ["gemini-2.0-flash"]},
        {"o1": ["gemini-2.0-flash"]},
    ],  # Specific fallbacks for context window exceeded errors
)

# Global cost tracking with thread safety
_cost_lock = threading.Lock()
_total_cost = 0.0


def get_total_cost() -> float:
    """Return the current total cost of all LLM API calls."""
    with _cost_lock:
        return _total_cost


def reset_cost_tracker() -> None:
    """Reset the cost tracker to zero."""
    global _total_cost
    with _cost_lock:
        _total_cost = 0.0


def add_to_total_cost(cost: float) -> None:
    """Add a cost amount to the total cost tracker."""
    global _total_cost
    with _cost_lock:
        _total_cost += cost
    logging.info(f"Added ${cost:.6f} to total. Current total: ${_total_cost:.6f}")


def text_cost_parser(completion: Any) -> tuple[str, float]:
    """
    Given LLM chat completion, return the text and the cost.
    Also adds the cost to the global cost tracker.
    """
    content = completion.choices[0].message.content
    cost = completion_cost(completion)

    # Update global cost tracker
    add_to_total_cost(cost)

    return content, cost


async def generate_response(
    messages: List[Dict[str, str]],
    model_name: str = "gpt-4o-mini",
    response_model: Optional[BaseModel] = None,
    temperature: float = 0.3,
    max_tokens: Optional[int] = None,
) -> Any:
    """
    Generate a response using the litellm Router.

    Args:
        messages: List of message dicts (role, content)
        model_name: Model name for router
        response_model: Optional Pydantic model for structured output
        temperature: Temperature for generation
        max_tokens: Maximum tokens to generate

    Returns:
        Response from the model (structured if response_model provided)
    """
    try:
        model_kwargs = {
            "temperature": temperature,
        }

        if max_tokens:
            model_kwargs["max_tokens"] = max_tokens

        if response_model:
            model_kwargs["response_format"] = response_model

        # Use litellm router for the completion
        response = await router.acompletion(
            model=model_name, messages=messages, **model_kwargs
        )
        response, cost = text_cost_parser(response)
        datamodel = response_model(**json.loads(response))
        return datamodel

    except Exception as e:
        logging.error("Error generating response: {}".format(e))
        raise


async def generate_mdc_response(
    system_prompt: str,
    user_prompt: str,
    model_name: str = "gpt-4o-mini",
    temperature: float = 0.3,
) -> MDCResponse:
    """
    Generate an MDC response using the litellm Router.

    Args:
        system_prompt: System prompt for the model
        user_prompt: User prompt for the model
        model_name: Model name for router (may be overridden based on token count)
        temperature: Temperature for generation

    Returns:
        MDCResponse object with structured output
    """
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    # Calculate token count for context window management
    tokenizer = get_tokenizer("gpt-4o")
    messages_tokens = 0
    for message in messages:
        messages_tokens += len(tokenize(message["content"], tokenizer))
    print("\033[91m" + f"Messages tokens: {messages_tokens}" + "\033[0m")

    # For extremely large content, still use the chunking approach
    if messages_tokens > 1000000:  # >1M tokens
        return await process_large_content(system_prompt, user_prompt, temperature)

    # For content within Gemini's context window but large, start with Gemini directly
    elif messages_tokens > 200000:  # 200K-1M tokens
        selected_model = "gemini-2.0-flash"
    # For medium-sized content, start with Claude
    elif messages_tokens > 128000:  # 128K-200K tokens
        selected_model = "claude-3-5-sonnet-latest"
    # For smaller content, use the requested model
    else:  # <128K tokens
        selected_model = model_name

    # Use selected model with LiteLLM's automatic fallbacks
    try:
        return await generate_response(
            messages=messages,
            model_name=selected_model,
            response_model=MDCResponse,
            temperature=temperature,
        )
    except Exception as e:
        logging.error(f"Error with model {selected_model}: {e}")
        # If we're already using Gemini and still failing, resort to chunking
        if selected_model == "gemini-2.0-flash-exp":
            logging.info("Falling back to chunking approach for very large content")
            return await process_large_content(system_prompt, user_prompt, temperature)
        # Otherwise, let the exception propagate (LiteLLM will handle fallbacks)
        raise


async def process_large_content(
    system_prompt: str, user_prompt: str, temperature: float = 0.3
) -> MDCResponse:
    """
    Process content that exceeds the 1M token limit by:
    1. Splitting into chunks and processing each chunk separately
    2. Making a second call with all chunk results combined to generate one final output

    Args:
        system_prompt: System prompt for the model
        user_prompt: User prompt containing large content
        temperature: Temperature for generation

    Returns:
        Combined MDCResponse from all chunks
    """
    # Estimate chunk size (approx. 800K tokens per chunk for safety margin)
    chunk_size = 800000

    # Split user content (assuming code is the main content to split)
    tokenizer = get_tokenizer("gpt-4o")
    user_tokens = tokenize(user_prompt, tokenizer)

    chunks = []
    start_idx = 0

    while start_idx < len(user_tokens):
        end_idx = min(start_idx + chunk_size, len(user_tokens))
        # Convert token indices back to text
        chunk_text = tokenizer.decode(user_tokens[start_idx:end_idx])

        # Add context information to each chunk
        chunk_prompt = f"[CHUNK {len(chunks)+1} of a large codebase] {chunk_text}"
        chunks.append(chunk_prompt)

        start_idx = end_idx

    logging.info(f"Split large content into {len(chunks)} chunks for processing")

    # Process each chunk with the appropriate model (using Gemini for large chunks)
    chunk_tasks = [
        generate_response(
            messages=[
                {
                    "role": "system",
                    "content": f"{system_prompt} You are processing part {i+1} of {len(chunks)} of a large codebase.",
                },
                {"role": "user", "content": chunk},
            ],
            model_name="gemini-2.0-flash-exp",
            response_model=MDCResponse,
            temperature=temperature,
        )
        for i, chunk in enumerate(chunks)
    ]

    chunk_results = await asyncio.gather(*chunk_tasks, return_exceptions=True)

    # Filter out exceptions and process valid results
    valid_results = [r for r in chunk_results if not isinstance(r, Exception)]

    if not valid_results:
        raise Exception("All chunks failed to process")

    # STEP 2: Make a second call with the combined MDC outputs
    # Convert each MDC result to a string representation
    mdc_outputs = []
    for i, result in enumerate(valid_results):
        mdc_str = f"--- MDC OUTPUT FROM CHUNK {i+1} ---\n"
        mdc_str += f"Summary: {result.summary}\n\n"
        mdc_str += f"Documentation: {result.documentation}\n\n"
        mdc_str += f"Functions: {result.functions}\n\n"
        mdc_str += f"Use Cases: {result.use_cases}\n\n"
        mdc_outputs.append(mdc_str)

    # Create a prompt for the second call
    consolidation_prompt = format_consolidation_prompt(valid_results, mdc_outputs)

    # Make the final call to combine results (using a model with smaller context since combined MDCs are much smaller)
    final_result = await generate_response(
        messages=[
            {
                "role": "system",
                "content": "You are an expert at synthesizing and combining documentation from multiple sources.",
            },
            {"role": "user", "content": consolidation_prompt},
        ],
        model_name="gpt-4o",  # Using OpenAI for final synthesis (MDC outputs will be much smaller than original code)
        response_model=MDCResponse,
        temperature=temperature,
    )
    return final_result


async def batch_generate_mdc_responses(
    prompts: list[Dict[str, str]],
    model_name: Optional[str] = "gpt-4o-mini",
    model_names: Optional[list[str]] = None,
    temperature: float = 0.0,
) -> list[MDCResponse]:
    """
    Process a batch of MDC generation requests using the litellm Router.
    Lets LiteLLM router handle batching and rate limiting automatically.

    Args:
        prompts: List of dicts with 'system_prompt' and 'user_prompt'
        model_name: Optional model name for router (used if model_names is None)
        model_names: Optional list of model names, one per prompt (overrides model_name)
        temperature: Temperature for generation

    Returns:
        List of MDCResponse objects
    """
    # Reset cost tracker at the beginning of batch
    initial_cost = get_total_cost()

    # Prepare all messages
    all_messages = []
    for p in prompts:
        system_prompt = p.get(
            "system_prompt", "You are an expert code documentation specialist."
        )
        user_prompt = p["user_prompt"]

        # Format messages for this prompt
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        all_messages.append(messages)

    # Common model parameters
    model_kwargs = {"temperature": temperature, "response_format": MDCResponse}

    try:
        # If model_names is provided, use a different model for each prompt
        if model_names and len(model_names) == len(prompts):
            # Make all API calls concurrently with different models
            responses = await asyncio.gather(
                *(
                    router.acompletion(
                        model=model_names[i], messages=messages, **model_kwargs
                    )
                    for i, messages in enumerate(all_messages)
                ),
                return_exceptions=True,
            )
        else:
            # Use the same model for all prompts
            responses = await asyncio.gather(
                *(
                    router.acompletion(
                        model=model_name, messages=messages, **model_kwargs
                    )
                    for messages in all_messages
                ),
                return_exceptions=True,
            )

        # Process responses
        results = []
        for i, response in enumerate(responses):
            if isinstance(response, Exception):
                model_used = model_names[i] if model_names else model_name
                logging.error(
                    f"Error processing prompt {i} with model {model_used}: {response}"
                )
                results.append(None)
            else:
                try:
                    content, cost = text_cost_parser(response)
                    datamodel = MDCResponse(**json.loads(content))
                    results.append(datamodel)
                except Exception as e:
                    logging.error(f"Error parsing response {i}: {e}")
                    results.append(None)

        # Log batch cost summary
        batch_cost = get_total_cost() - initial_cost
        logging.info(f"===== BATCH COST SUMMARY =====")
        logging.info(
            f"Processed {len(prompts)} prompts for a total cost of ${batch_cost:.6f}"
        )
        logging.info(f"Average cost per prompt: ${batch_cost/len(prompts):.6f}")
        print(
            f"\033[92mBatch processing complete. Total cost: ${batch_cost:.6f}\033[0m"
        )

        return results

    except Exception as e:
        logging.error(f"Batch processing failed: {e}")
        raise
