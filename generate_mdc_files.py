#!/usr/bin/env python3
"""
MDC File Generator for Repository Documentation

This script creates .mdc documentation files for the Cursor IDE based on
repository analysis. It uses the outputs from repo_analyzer.py to generate
contextual documentation for different parts of the codebase.
"""

import os
import json
import argparse
import logging
import asyncio
from openai import AsyncOpenAI
from instructor import from_openai
from pydantic import BaseModel, Field

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# Initialize OpenAI client with instructor
client = from_openai(AsyncOpenAI())


class MDCResponse(BaseModel):
    """Model for structured MDC file content generation."""
    description: str = Field(
        ...,
        description=(
            "A brief description of what this rule provides context for."
        )
    )
    globs: str = Field(
        ...,
        description="File patterns this rule applies to, using glob syntax."
    )
    always_apply: bool = Field(
        default=False,
        description=(
            "Whether this rule should always be applied regardless of file context."
        )
    )
    content: str = Field(
        ...,
        description=(
            "The markdown content providing useful documentation and context."
        )
    )


async def get_mdc_content(
    file_path, 
    summaries, 
    model_name="gpt-4o-mini", 
    temperature=0.3
):
    """
    Generate MDC file content using OpenAI API.
    
    Args:
        file_path: Path to the file or pattern for which to generate documentation
        summaries: Dictionary of file summaries from repo_analyzer
        model_name: OpenAI model to use
        temperature: Temperature for generation
        
    Returns:
        MDCResponse object with formatted MDC content
    """
    path_type = "directory" if file_path.endswith("*") else "file"
    base_path = file_path.replace("*", "")
    
    # Collect relevant summaries
    relevant_summaries = {}
    for summary_path, summary_data in summaries.items():
        path_dirname = os.path.dirname(summary_path)
        base_path_trimmed = base_path.rstrip("/")
        if summary_path.startswith(base_path) or (
            path_type == "directory" and 
            path_dirname == base_path_trimmed
        ):
            relevant_summaries[summary_path] = summary_data

    # Build the prompt
    prompt = f"""
You are tasked with creating documentation for a Cursor IDE rule that provides contextual help.
This rule will apply to: {file_path}

Here are summaries of relevant code components:

"""
    
    for path, data in relevant_summaries.items():
        prompt += f"\n## {path}\n"
        for item in data:
            item_summary = item['summary']
            item_name = item['name']
            item_type = item['type']
            prompt += f"- {item_name} ({item_type}): {item_summary}\n"
    
    prompt += f"""
Based on these summaries, create a .mdc file for Cursor IDE with:

1. A concise description field explaining what this rule covers
2. Appropriate glob patterns (already provided as: {file_path})
3. Whether this rule should always apply (typically false unless it's repository-wide guidance)
4. Detailed markdown content with:
   - Overview of purpose/functionality
   - Key components and their relationships
   - Usage examples where appropriate
   - Best practices and potential pitfalls
   - Any architectural patterns or design decisions

The output should be structured knowledge that helps developers understand this code quickly.
"""

    try:
        response = await client.chat.completions.create(
            model=model_name,
            response_model=MDCResponse,
            messages=[
                {
                    "role": "system", 
                    "content": (
                        "You are an expert code documentation specialist."
                    )
                },
                {"role": "user", "content": prompt},
            ],
            temperature=temperature,
        )
        return response
    except Exception as e:
        logging.error(f"Error calling OpenAI API: {e}")
        return MDCResponse(
            description=f"Documentation for {file_path}",
            globs=file_path,
            always_apply=False,
            content=f"Error generating documentation: {str(e)}"
        )


def write_mdc_file(output_path, mdc_content):
    """
    Write the MDC content to a file.
    
    Args:
        output_path: Path to write the MDC file
        mdc_content: MDCResponse object with the content
    """
    try:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            # Write the frontmatter
            f.write("---\n")
            f.write(f"description: {mdc_content.description}\n")
            f.write(f"globs: {mdc_content.globs}\n")
            f.write(f"alwaysApply: {str(mdc_content.always_apply).lower()}\n")
            f.write("---\n\n")
            
            # Write the content
            f.write(mdc_content.content)
        
        logging.info(f"MDC file created: {output_path}")
    except Exception as e:
        logging.error(f"Error writing MDC file {output_path}: {e}")


async def generate_file_specific_mdcs(repo_path, summaries_file, output_dir):
    """
    Generate MDC files for specific files in the repository.
    
    Args:
        repo_path: Path to the repository
        summaries_file: Path to the summaries.json file
        output_dir: Directory to output the MDC files
    """
    with open(summaries_file, 'r', encoding='utf-8') as f:
        summaries = json.load(f)
    
    # Generate MDC for each file
    tasks = []
    for file_path in summaries.keys():
        if file_path.endswith(".py"):
            file_mdc = f"{file_path}.mdc"
            output_path = os.path.join(output_dir, file_mdc)
            task = get_mdc_content(file_path, summaries)
            tasks.append((output_path, task))
    
    # Process results
    for output_path, task in tasks:
        mdc_content = await task
        write_mdc_file(output_path, mdc_content)


async def generate_directory_mdcs(repo_path, summaries_file, output_dir):
    """
    Generate MDC files for directories in the repository.
    
    Args:
        repo_path: Path to the repository
        summaries_file: Path to the summaries.json file
        output_dir: Directory to output the MDC files
    """
    with open(summaries_file, 'r', encoding='utf-8') as f:
        summaries = json.load(f)
    
    # Identify directories that contain Python files
    directories = set()
    for file_path in summaries.keys():
        if file_path.endswith(".py"):
            directory = os.path.dirname(file_path)
            if directory:
                directories.add(directory)
    
    # Generate MDC for each directory
    tasks = []
    for directory in directories:
        glob_pattern = f"{directory}/*"
        dir_path = f"{directory}/_directory.mdc"
        output_path = os.path.join(output_dir, dir_path)
        task = get_mdc_content(glob_pattern, summaries)
        tasks.append((output_path, task))
    
    # Process results
    for output_path, task in tasks:
        mdc_content = await task
        write_mdc_file(output_path, mdc_content)


async def generate_high_level_mdc(repo_path, summaries_file, output_dir):
    """
    Generate high-level MDC file for the entire repository or major components.
    
    Args:
        repo_path: Path to the repository
        summaries_file: Path to the summaries.json file
        output_dir: Directory to output the MDC files
    """
    with open(summaries_file, 'r', encoding='utf-8') as f:
        summaries = json.load(f)
    
    # Check if backend directory exists
    backend_exists = os.path.isdir(os.path.join(repo_path, "backend"))
    
    # Generate high-level MDC for the repository
    repo_output_path = os.path.join(output_dir, "_repository.mdc")
    repo_mdc = await get_mdc_content("*", summaries)
    write_mdc_file(repo_output_path, repo_mdc)
    
    # Generate backend-specific MDC if applicable
    if backend_exists:
        backend_file = "backend/_backend.mdc"
        backend_output_path = os.path.join(output_dir, backend_file)
        backend_mdc = await get_mdc_content("backend/*", summaries)
        write_mdc_file(backend_output_path, backend_mdc)


async def main():
    """Main function to parse arguments and run the MDC generation."""
    parser = argparse.ArgumentParser(
        description=(
            "Generate MDC documentation files from repository analysis"
        )
    )
    parser.add_argument(
        "--repo_path", 
        required=True, 
        help="Path to the repository"
    )
    parser.add_argument(
        "--summaries_file", 
        required=True, 
        help="Path to the summaries.json file from repo_analyzer"
    )
    parser.add_argument(
        "--output_dir", 
        default=".cursor/rules", 
        help="Output directory for MDC files"
    )
    parser.add_argument(
        "--model", 
        default="gpt-4o-mini", 
        help="OpenAI model to use for documentation generation"
    )
    args = parser.parse_args()
    
    # Set the OpenAI API key from environment
    if not os.environ.get("OPENAI_API_KEY"):
        logging.error("Error: OPENAI_API_KEY environment variable not set.")
        return
    
    # Ensure output directory exists
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Generate MDC files
    await generate_file_specific_mdcs(
        args.repo_path, args.summaries_file, args.output_dir
    )
    await generate_directory_mdcs(
        args.repo_path, args.summaries_file, args.output_dir
    )
    await generate_high_level_mdc(
        args.repo_path, args.summaries_file, args.output_dir
    )
    
    complete_msg = f"MDC generation complete! Files saved to {args.output_dir}"
    logging.info(complete_msg)


if __name__ == "__main__":
    asyncio.run(main()) 