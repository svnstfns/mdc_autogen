"""
FastAPI-based key provider for retrieving LLM API keys from a FastAPI service.
"""

import os
import logging
from typing import Optional, Dict
from .key_provider import KeyProvider

try:
    import requests
except ImportError:
    requests = None


class FastAPIKeyProvider(KeyProvider):
    """Provides API keys through a FastAPI service."""

    def __init__(
        self,
        api_endpoint: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        """
        Initialize FastAPI key provider.

        Args:
            api_endpoint: FastAPI endpoint URL for retrieving keys
            api_key: API key for authenticating with the FastAPI service
        """
        self.api_endpoint = api_endpoint or os.environ.get("FASTAPI_KEY_ENDPOINT")
        self.api_key = api_key or os.environ.get("FASTAPI_API_KEY")
        self._keys_cache: Dict[str, str] = {}

    def _fetch_keys(self) -> bool:
        """
        Fetch API keys from the FastAPI endpoint.

        Returns:
            True if keys fetched successfully, False otherwise
        """
        if requests is None:
            logging.warning("requests library not installed, FastAPI key provider unavailable")
            return False

        if not self.api_endpoint:
            logging.debug("FastAPI endpoint not configured")
            return False

        try:
            headers = {}
            if self.api_key:
                headers["X-API-Key"] = self.api_key
            
            response = requests.get(
                f"{self.api_endpoint}/llm-keys",
                headers=headers,
                timeout=10,
            )
            response.raise_for_status()
            keys_data = response.json()
            
            # Expected format: {"openai": "key1", "anthropic": "key2", ...}
            if isinstance(keys_data, dict):
                self._keys_cache = keys_data
                return True
            return False
        except Exception as e:
            logging.error(f"Failed to fetch keys from FastAPI endpoint: {e}")
            return False

    def get_key(self, provider: str) -> Optional[str]:
        """
        Get API key for a specific provider from FastAPI service.

        Args:
            provider: The LLM provider name

        Returns:
            API key if available, None otherwise
        """
        if not self._keys_cache:
            if not self._fetch_keys():
                return None
        
        return self._keys_cache.get(provider.lower())

    def is_available(self) -> bool:
        """
        Check if FastAPI key provider is configured.

        Returns:
            True if FastAPI endpoint is configured, False otherwise
        """
        return bool(self.api_endpoint)
