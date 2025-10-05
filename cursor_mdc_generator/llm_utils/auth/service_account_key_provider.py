"""
Service Account-based key provider for authenticating and retrieving LLM API keys.
"""

import os
import logging
import json
from typing import Optional, Dict
from pathlib import Path
from .key_provider import KeyProvider

try:
    import requests
except ImportError:
    requests = None


class ServiceAccountKeyProvider(KeyProvider):
    """Provides API keys through service account authentication."""

    def __init__(
        self,
        service_account_file: Optional[str] = None,
        key_endpoint: Optional[str] = None,
    ):
        """
        Initialize service account key provider.

        Args:
            service_account_file: Path to service account JSON file
            key_endpoint: Endpoint to retrieve API keys using service account
        """
        self.service_account_file = service_account_file or os.environ.get(
            "SERVICE_ACCOUNT_FILE"
        )
        self.key_endpoint = key_endpoint or os.environ.get("SERVICE_ACCOUNT_KEY_ENDPOINT")
        self._service_account_data: Optional[Dict] = None
        self._keys_cache: Dict[str, str] = {}

    def _load_service_account(self) -> bool:
        """
        Load service account credentials from file.

        Returns:
            True if loaded successfully, False otherwise
        """
        if not self.service_account_file:
            logging.debug("Service account file not configured")
            return False

        try:
            file_path = Path(self.service_account_file)
            if not file_path.exists():
                logging.error(f"Service account file not found: {self.service_account_file}")
                return False

            with open(file_path, "r") as f:
                self._service_account_data = json.load(f)
            return True
        except Exception as e:
            logging.error(f"Failed to load service account file: {e}")
            return False

    def _fetch_keys(self) -> bool:
        """
        Fetch API keys using service account credentials.

        Returns:
            True if keys fetched successfully, False otherwise
        """
        if requests is None:
            logging.warning("requests library not installed, service account authentication unavailable")
            return False

        if not self._service_account_data:
            if not self._load_service_account():
                return False

        if not self.key_endpoint:
            logging.debug("Service account key endpoint not configured")
            return False

        try:
            # Use service account credentials to authenticate
            # The exact implementation depends on your service account format
            auth_header = self._service_account_data.get("token") or \
                         self._service_account_data.get("api_key")
            
            if not auth_header:
                logging.error("Service account file missing authentication credentials")
                return False

            response = requests.get(
                self.key_endpoint,
                headers={
                    "Authorization": f"Bearer {auth_header}",
                    "X-Service-Account": self._service_account_data.get("client_id", ""),
                },
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
            logging.error(f"Failed to fetch keys using service account: {e}")
            return False

    def get_key(self, provider: str) -> Optional[str]:
        """
        Get API key for a specific provider using service account.

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
        Check if service account authentication is configured.

        Returns:
            True if service account is configured, False otherwise
        """
        return bool(self.service_account_file and self.key_endpoint)
