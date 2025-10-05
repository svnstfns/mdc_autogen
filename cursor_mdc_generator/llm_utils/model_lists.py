from .auth import get_key_manager

# Get the key manager instance
_key_manager = get_key_manager()

# Build chat model list with keys from the key manager
chat_model_list = [
    {
        "model_name": "gpt-4o-mini",  # model alias -> loadbalance between models with same `model_name`
        "litellm_params": {
            "model": "openai/gpt-4o-mini",  # actual model name
            "api_key": _key_manager.get_key("openai"),
            "rpm": 10000,
            "tpm": 10000000,
        },
    },
    {
        "model_name": "gpt-4o",
        "litellm_params": {
            "model": "openai/gpt-4o",
            "api_key": _key_manager.get_key("openai"),
            "rpm": 10000,
            "tpm": 10000000,
        },
    },
    {
        "model_name": "o1-preview",
        "litellm_params": {
            "model": "openai/o1-preview",
            "api_key": _key_manager.get_key("openai"),
            "rpm": 10000,
            "tpm": 10000000,
        },
    },
    {
        "model_name": "o1",
        "litellm_params": {
            "model": "openai/o1",
            "api_key": _key_manager.get_key("openai"),
            "rpm": 10000,
            "tpm": 10000000,
        },
    },
    {
        "model_name": "o3-mini",
        "litellm_params": {
            "model": "openai/o3-mini",
            "api_key": _key_manager.get_key("openai"),
            "rpm": 10000,
            "tpm": 10000000,
        },
    },
    {
        "model_name": "claude-3-5-sonnet-20241022",
        "litellm_params": {
            "model": "anthropic/claude-3-5-sonnet-20241022",
            "api_key": _key_manager.get_key("anthropic"),
            "rpm": 4000,
            "tpm": 40000,
        },
    },
    {
        "model_name": "deepseek-chat",
        "litellm_params": {
            "model": "deepseek/deepseek-chat",
            "api_key": _key_manager.get_key("deepseek"),
            "rpm": 10000,
            "tpm": 10000000,
        },
    },
    {
        "model_name": "deepseek-reasoner",
        "litellm_params": {
            "model": "deepseek/deepseek-reasoner",
            "api_key": _key_manager.get_key("deepseek"),
            "rpm": 10000,
            "tpm": 10000000,
        },
    },
    {
        "model_name": "gemini-2.0-flash",
        "litellm_params": {
            "model": "gemini/gemini-2.0-flash",
            "api_key": _key_manager.get_key("gemini"),
            "rpm": 10000,
            "tpm": 10000000,
        },
    },
]
