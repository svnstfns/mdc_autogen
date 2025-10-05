"""
Base interface for LLM API key providers.
"""

from abc import ABC, abstractmethod
from typing import Optional


class KeyProvider(ABC):
    """Abstract base class for API key providers."""

    @abstractmethod
    def get_key(self, provider: str) -> Optional[str]:
        """
        Get API key for a specific provider.

        Args:
            provider: The LLM provider name (e.g., 'openai', 'anthropic', 'gemini', 'deepseek')

        Returns:
            API key if available, None otherwise
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """
        Check if this key provider is available/configured.

        Returns:
            True if the provider is available, False otherwise
        """
        pass
