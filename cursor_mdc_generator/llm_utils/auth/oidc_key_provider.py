"""
OIDC-based key provider for authenticating and retrieving LLM API keys.
"""

import os
import logging
from typing import Optional, Dict
import json
from .key_provider import KeyProvider

try:
    import requests
except ImportError:
    requests = None


class OIDCKeyProvider(KeyProvider):
    """Provides API keys through OIDC authentication."""

    def __init__(
        self,
        token_endpoint: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        key_endpoint: Optional[str] = None,
    ):
        """
        Initialize OIDC key provider.

        Args:
            token_endpoint: OIDC token endpoint URL
            client_id: OIDC client ID
            client_secret: OIDC client secret
            key_endpoint: Endpoint to retrieve API keys after authentication
        """
        self.token_endpoint = token_endpoint or os.environ.get("OIDC_TOKEN_ENDPOINT")
        self.client_id = client_id or os.environ.get("OIDC_CLIENT_ID")
        self.client_secret = client_secret or os.environ.get("OIDC_CLIENT_SECRET")
        self.key_endpoint = key_endpoint or os.environ.get("OIDC_KEY_ENDPOINT")
        self._access_token: Optional[str] = None
        self._keys_cache: Dict[str, str] = {}

    def _authenticate(self) -> bool:
        """
        Authenticate with OIDC provider and get access token.

        Returns:
            True if authentication successful, False otherwise
        """
        if requests is None:
            logging.warning("requests library not installed, OIDC authentication unavailable")
            return False

        if not all([self.token_endpoint, self.client_id, self.client_secret]):
            logging.debug("OIDC credentials not configured")
            return False

        try:
            response = requests.post(
                self.token_endpoint,
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                },
                timeout=10,
            )
            response.raise_for_status()
            token_data = response.json()
            self._access_token = token_data.get("access_token")
            return self._access_token is not None
        except Exception as e:
            logging.error(f"OIDC authentication failed: {e}")
            return False

    def _fetch_keys(self) -> bool:
        """
        Fetch API keys from the key endpoint using the access token.

        Returns:
            True if keys fetched successfully, False otherwise
        """
        if requests is None:
            return False

        if not self._access_token:
            if not self._authenticate():
                return False

        if not self.key_endpoint:
            logging.debug("OIDC key endpoint not configured")
            return False

        try:
            response = requests.get(
                self.key_endpoint,
                headers={"Authorization": f"Bearer {self._access_token}"},
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
            logging.error(f"Failed to fetch keys from OIDC endpoint: {e}")
            return False

    def get_key(self, provider: str) -> Optional[str]:
        """
        Get API key for a specific provider through OIDC.

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
        Check if OIDC authentication is configured.

        Returns:
            True if OIDC is configured, False otherwise
        """
        return all([self.token_endpoint, self.client_id, self.client_secret, self.key_endpoint])
