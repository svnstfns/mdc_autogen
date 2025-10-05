"""
Environment variable-based key provider.
This is the legacy method of providing API keys.
"""

import os
from typing import Optional
from .key_provider import KeyProvider


class EnvironmentKeyProvider(KeyProvider):
    """Provides API keys from environment variables."""

    # Mapping of provider names to environment variable names
    ENV_VAR_MAPPING = {
        "openai": "OPENAI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "gemini": "GEMINI_API_KEY",
        "deepseek": "DEEPSEEK_API_KEY",
    }

    def get_key(self, provider: str) -> Optional[str]:
        """
        Get API key from environment variable.

        Args:
            provider: The LLM provider name

        Returns:
            API key from environment variable if set, None otherwise
        """
        env_var = self.ENV_VAR_MAPPING.get(provider.lower())
        if env_var:
            return os.environ.get(env_var)
        return None

    def is_available(self) -> bool:
        """
        Check if any API keys are available in environment variables.

        Returns:
            True if at least one API key is set, False otherwise
        """
        return any(
            os.environ.get(env_var) for env_var in self.ENV_VAR_MAPPING.values()
        )
