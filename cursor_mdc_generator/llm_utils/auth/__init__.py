"""
Authentication module for LLM API keys.
Supports multiple authentication methods: environment variables, OIDC, service accounts, and FastAPI.
"""

from .key_provider import KeyProvider
from .env_key_provider import EnvironmentKeyProvider
from .oidc_key_provider import OIDCKeyProvider
from .service_account_key_provider import ServiceAccountKeyProvider
from .fastapi_key_provider import FastAPIKeyProvider
from .key_manager import KeyManager, get_key_manager, set_key_manager

__all__ = [
    "KeyProvider",
    "EnvironmentKeyProvider",
    "OIDCKeyProvider",
    "ServiceAccountKeyProvider",
    "FastAPIKeyProvider",
    "KeyManager",
    "get_key_manager",
    "set_key_manager",
]
