import os

chat_model_list = [
    {
        "model_name": "gpt-4o-mini",  # model alias -> loadbalance between models with same `model_name`
        "litellm_params": {
            "model": "openai/gpt-4o-mini",  # actual model name
            "api_key": os.getenv("OPENAI_API_KEY"),
            "rpm": 10000,
            "tpm": 10000000,
        },
    },
    {
        "model_name": "gpt-4o",
        "litellm_params": {
            "model": "openai/gpt-4o",
            "api_key": os.getenv("OPENAI_API_KEY"),
            "rpm": 10000,
            "tpm": 10000000,
        },
    },
    {
        "model_name": "o1-preview",
        "litellm_params": {
            "model": "openai/o1-preview",
            "api_key": os.getenv("OPENAI_API_KEY"),
            "rpm": 10000,
            "tpm": 10000000,
        },
    },
    {
        "model_name": "o1",
        "litellm_params": {
            "model": "openai/o1",
            "api_key": os.getenv("OPENAI_API_KEY"),
            "rpm": 10000,
            "tpm": 10000000,
        },
    },
    {
        "model_name": "o3-mini",
        "litellm_params": {
            "model": "openai/o3-mini",
            "api_key": os.getenv("OPENAI_API_KEY"),
            "rpm": 10000,
            "tpm": 10000000,
        },
    },
    {
        "model_name": "claude-3-5-sonnet-20241022",
        "litellm_params": {
            "model": "anthropic/claude-3-5-sonnet-20241022",
            "api_key": os.getenv("ANTHROPIC_API_KEY"),
            "rpm": 4000,
            "tpm": 40000,
        },
    },
    {
        "model_name": "deepseek-chat",
        "litellm_params": {
            "model": "deepseek/deepseek-chat",
            "api_key": os.getenv("DEEPSEEK_API_KEY"),
            "rpm": 10000,
            "tpm": 10000000,
        },
    },
    {
        "model_name": "deepseek-reasoner",
        "litellm_params": {
            "model": "deepseek/deepseek-reasoner",
            "api_key": os.getenv("DEEPSEEK_API_KEY"),
            "rpm": 10000,
            "tpm": 10000000,
        },
    },
    {
        "model_name": "gemini-2.0-flash",
        "litellm_params": {
            "model": "gemini/gemini-2.0-flash",
            "api_key": os.getenv("GEMINI_API_KEY"),
            "rpm": 10000,
            "tpm": 10000000,
        },
    },
]
