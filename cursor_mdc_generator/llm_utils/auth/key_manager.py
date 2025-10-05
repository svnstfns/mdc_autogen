"""
Key manager for coordinating multiple key providers.
"""

import logging
from typing import Optional, List
from .key_provider import KeyProvider
from .env_key_provider import EnvironmentKeyProvider
from .oidc_key_provider import OIDCKeyProvider
from .service_account_key_provider import ServiceAccountKeyProvider
from .fastapi_key_provider import FastAPIKeyProvider


class KeyManager:
    """Manages multiple key providers and provides a unified interface for key retrieval."""

    def __init__(self, providers: Optional[List[KeyProvider]] = None):
        """
        Initialize key manager with a list of providers.

        Args:
            providers: List of key providers to use. If None, uses default providers.
        """
        if providers is None:
            # Default provider order: FastAPI > Service Account > OIDC > Environment
            # This allows for more secure methods to override environment variables
            self.providers = [
                FastAPIKeyProvider(),
                ServiceAccountKeyProvider(),
                OIDCKeyProvider(),
                EnvironmentKeyProvider(),
            ]
        else:
            self.providers = providers

    def get_key(self, provider: str) -> Optional[str]:
        """
        Get API key for a specific provider from the first available source.

        Args:
            provider: The LLM provider name (e.g., 'openai', 'anthropic', 'gemini', 'deepseek')

        Returns:
            API key if available from any provider, None otherwise
        """
        for key_provider in self.providers:
            try:
                if key_provider.is_available():
                    key = key_provider.get_key(provider)
                    if key:
                        logging.debug(
                            f"API key for {provider} obtained from {key_provider.__class__.__name__}"
                        )
                        return key
            except Exception as e:
                logging.warning(
                    f"Error getting key from {key_provider.__class__.__name__}: {e}"
                )
                continue

        logging.debug(f"No API key found for provider: {provider}")
        return None

    def has_any_key(self) -> bool:
        """
        Check if any API key is available from any provider.

        Returns:
            True if at least one key is available, False otherwise
        """
        providers = ["openai", "anthropic", "gemini", "deepseek"]
        return any(self.get_key(provider) for provider in providers)

    def get_available_providers(self) -> List[str]:
        """
        Get list of LLM providers that have API keys available.

        Returns:
            List of provider names with available keys
        """
        providers = ["openai", "anthropic", "gemini", "deepseek"]
        return [p for p in providers if self.get_key(p)]


# Global key manager instance
_key_manager: Optional[KeyManager] = None


def get_key_manager() -> KeyManager:
    """
    Get the global key manager instance.

    Returns:
        Global KeyManager instance
    """
    global _key_manager
    if _key_manager is None:
        _key_manager = KeyManager()
    return _key_manager


def set_key_manager(key_manager: KeyManager) -> None:
    """
    Set a custom key manager instance.

    Args:
        key_manager: KeyManager instance to use globally
    """
    global _key_manager
    _key_manager = key_manager
