# LLM Authentication Module

This module provides a flexible authentication system for obtaining LLM API keys through multiple methods.

## Supported Authentication Methods

### 1. Environment Variables (Legacy)

The traditional method of providing API keys through environment variables.

**Environment Variables:**
- `OPENAI_API_KEY` - OpenAI API key
- `ANTHROPIC_API_KEY` - Anthropic (Claude) API key
- `GEMINI_API_KEY` - Google Gemini API key
- `DEEPSEEK_API_KEY` - DeepSeek API key

**Example:**
```bash
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-ant-..."
mdcgen /path/to/repo
```

### 2. OIDC Authentication

Authenticate using OpenID Connect (OIDC) and retrieve API keys from a secure endpoint.

**Environment Variables:**
- `OIDC_TOKEN_ENDPOINT` - OIDC token endpoint URL
- `OIDC_CLIENT_ID` - OIDC client ID
- `OIDC_CLIENT_SECRET` - OIDC client secret
- `OIDC_KEY_ENDPOINT` - Endpoint to retrieve API keys after authentication

**Example:**
```bash
export OIDC_TOKEN_ENDPOINT="https://auth.example.com/oauth/token"
export OIDC_CLIENT_ID="your-client-id"
export OIDC_CLIENT_SECRET="your-client-secret"
export OIDC_KEY_ENDPOINT="https://keys.example.com/api/llm-keys"
mdcgen /path/to/repo
```

The key endpoint should return a JSON response with provider names as keys:
```json
{
  "openai": "sk-...",
  "anthropic": "sk-ant-...",
  "gemini": "...",
  "deepseek": "..."
}
```

### 3. Service Account

Authenticate using a service account file and retrieve API keys from a secure endpoint.

**Environment Variables:**
- `SERVICE_ACCOUNT_FILE` - Path to service account JSON file
- `SERVICE_ACCOUNT_KEY_ENDPOINT` - Endpoint to retrieve API keys

**Service Account File Format:**
```json
{
  "client_id": "service-account-id",
  "token": "service-account-token",
  "api_key": "service-account-api-key"
}
```

**Example:**
```bash
export SERVICE_ACCOUNT_FILE="/path/to/service-account.json"
export SERVICE_ACCOUNT_KEY_ENDPOINT="https://keys.example.com/api/llm-keys"
mdcgen /path/to/repo
```

### 4. FastAPI Service

Retrieve API keys from a FastAPI service endpoint.

**Environment Variables:**
- `FASTAPI_KEY_ENDPOINT` - FastAPI service base URL
- `FASTAPI_API_KEY` - (Optional) API key for authenticating with the FastAPI service

**Example:**
```bash
export FASTAPI_KEY_ENDPOINT="https://api.example.com"
export FASTAPI_API_KEY="your-api-key"  # Optional
mdcgen /path/to/repo
```

The FastAPI service should expose an endpoint at `/llm-keys` that returns:
```json
{
  "openai": "sk-...",
  "anthropic": "sk-ant-...",
  "gemini": "...",
  "deepseek": "..."
}
```

## Provider Priority

When multiple authentication methods are configured, the system uses this priority order:

1. FastAPI Service
2. Service Account
3. OIDC
4. Environment Variables

The first method that provides a valid key is used.

## Programmatic Usage

### Using the Key Manager

```python
from cursor_mdc_generator.llm_utils.auth import get_key_manager

# Get the global key manager instance
key_manager = get_key_manager()

# Get a key for a specific provider
openai_key = key_manager.get_key("openai")
anthropic_key = key_manager.get_key("anthropic")

# Check if any keys are available
if key_manager.has_any_key():
    print("At least one API key is available")

# Get list of available providers
providers = key_manager.get_available_providers()
print(f"Available providers: {providers}")
```

### Using a Custom Key Manager

```python
from cursor_mdc_generator.llm_utils.auth import (
    KeyManager,
    FastAPIKeyProvider,
    EnvironmentKeyProvider,
    set_key_manager,
)

# Create a custom key manager with specific providers
custom_manager = KeyManager(
    providers=[
        FastAPIKeyProvider(api_endpoint="https://api.example.com"),
        EnvironmentKeyProvider(),
    ]
)

# Set it as the global key manager
set_key_manager(custom_manager)
```

### Implementing a Custom Provider

```python
from cursor_mdc_generator.llm_utils.auth import KeyProvider
from typing import Optional

class CustomKeyProvider(KeyProvider):
    def get_key(self, provider: str) -> Optional[str]:
        # Your custom logic to retrieve keys
        return None
    
    def is_available(self) -> bool:
        # Check if your provider is configured
        return True
```

## Security Considerations

1. **Never commit API keys to version control**
2. **Use secure methods (OIDC, Service Account, FastAPI) in production**
3. **Rotate API keys regularly**
4. **Use environment variables only for local development**
5. **Ensure HTTPS is used for all API endpoints**
6. **Implement proper access controls on key endpoints**

## Troubleshooting

### No API keys found

If you see an error message about no API keys being found, ensure that:

1. At least one authentication method is properly configured
2. Environment variables are exported in your current shell
3. Service account files exist and are readable
4. API endpoints are accessible and returning valid responses

### Debug logging

Enable debug logging to see which provider is being used:

```bash
mdcgen /path/to/repo --log-level DEBUG
```

This will show messages like:
```
DEBUG - API key for openai obtained from EnvironmentKeyProvider
```
