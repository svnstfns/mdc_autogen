# Authentication System

## Overview

The mdcgen tool now supports multiple authentication methods for obtaining LLM API keys, providing flexibility for different deployment scenarios from local development to enterprise production environments.

## Quick Start

### For Local Development (Environment Variables)

```bash
export OPENAI_API_KEY="sk-..."
mdcgen /path/to/repo
```

### For Enterprise (OIDC)

```bash
export OIDC_TOKEN_ENDPOINT="https://auth.company.com/oauth/token"
export OIDC_CLIENT_ID="mdcgen-client"
export OIDC_CLIENT_SECRET="secret"
export OIDC_KEY_ENDPOINT="https://keys.company.com/api/llm-keys"
mdcgen /path/to/repo
```

## Supported Methods

### 1. Environment Variables
**Best for:** Local development, CI/CD pipelines

Simple key configuration through environment variables:
- `OPENAI_API_KEY`
- `ANTHROPIC_API_KEY`
- `GEMINI_API_KEY`
- `DEEPSEEK_API_KEY`

### 2. OIDC Authentication
**Best for:** Enterprise SSO integration, centralized identity management

Authenticate using OpenID Connect providers:
- Works with Keycloak, Auth0, Okta, Azure AD, etc.
- Provides audit trails
- Supports token expiration and rotation
- Centralized access control

### 3. Service Account
**Best for:** Automated systems, cloud deployments

Use service account credentials files:
- Compatible with GCP, AWS, and custom formats
- Integrates with secret managers (Vault, AWS Secrets Manager, etc.)
- Supports credential rotation
- Minimal manual configuration

### 4. FastAPI Service
**Best for:** Custom key management systems, multi-tenant setups

Retrieve keys from a FastAPI service:
- Centralized key management
- Custom authentication logic
- Dynamic key provisioning
- Usage tracking and monitoring

## Priority Order

When multiple methods are configured, keys are obtained in this order:

1. **FastAPI Service** (highest priority)
2. **Service Account**
3. **OIDC**
4. **Environment Variables** (fallback)

The first method that successfully provides a key is used.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        KeyManager                           │
│  (Orchestrates multiple providers with fallback logic)     │
└─────────────────────────────────────────────────────────────┘
                              │
           ┌──────────────────┼──────────────────┐
           │                  │                  │
           ▼                  ▼                  ▼
┌──────────────────┐  ┌──────────────┐  ┌──────────────┐
│  FastAPIProvider │  │ OIDCProvider │  │ EnvProvider  │
└──────────────────┘  └──────────────┘  └──────────────┘
           │                  │                  │
           └──────────────────┴──────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │   LLM API Keys   │
                    └──────────────────┘
```

## Files Modified

### Core Implementation
- `cursor_mdc_generator/llm_utils/auth/` - New authentication module
  - `key_provider.py` - Base interface
  - `env_key_provider.py` - Environment variable support
  - `oidc_key_provider.py` - OIDC authentication
  - `service_account_key_provider.py` - Service account support
  - `fastapi_key_provider.py` - FastAPI integration
  - `key_manager.py` - Provider orchestration

### Integration Points
- `cursor_mdc_generator/llm_utils/model_lists.py` - Uses key manager for API keys
- `cursor_mdc_generator/cli.py` - Enhanced error messages, key validation

### Configuration
- `pyproject.toml` - Added `requests` dependency

## Documentation

Comprehensive guides available:
- [Authentication Overview](cursor_mdc_generator/llm_utils/auth/README.md)
- [FastAPI Service Example](cursor_mdc_generator/llm_utils/auth/FASTAPI_EXAMPLE.md)
- [OIDC Setup Guide](cursor_mdc_generator/llm_utils/auth/OIDC_EXAMPLE.md)
- [Service Account Guide](cursor_mdc_generator/llm_utils/auth/SERVICE_ACCOUNT_EXAMPLE.md)
- [Example Scripts](examples/)

## Migration Guide

### From Environment Variables Only

If you're currently using:
```bash
export OPENAI_API_KEY="sk-..."
mdcgen /path/to/repo
```

**No changes needed!** The system is fully backward compatible. Your existing setup continues to work.

### To OIDC Authentication

1. Set up your OIDC provider (Keycloak, Auth0, etc.)
2. Configure environment variables:
   ```bash
   export OIDC_TOKEN_ENDPOINT="https://auth.example.com/oauth/token"
   export OIDC_CLIENT_ID="your-client-id"
   export OIDC_CLIENT_SECRET="your-client-secret"
   export OIDC_KEY_ENDPOINT="https://keys.example.com/api/llm-keys"
   ```
3. Remove old environment variables (optional):
   ```bash
   unset OPENAI_API_KEY ANTHROPIC_API_KEY
   ```
4. Test:
   ```bash
   mdcgen /path/to/repo --log-level DEBUG
   ```

### To Service Account

1. Create a service account file:
   ```json
   {
     "client_id": "mdcgen-service",
     "token": "your-token",
     "type": "service_account"
   }
   ```
2. Configure:
   ```bash
   export SERVICE_ACCOUNT_FILE="/path/to/service-account.json"
   export SERVICE_ACCOUNT_KEY_ENDPOINT="https://keys.example.com/api/llm-keys"
   ```
3. Test:
   ```bash
   mdcgen /path/to/repo
   ```

## Programmatic Usage

```python
from cursor_mdc_generator.llm_utils.auth import get_key_manager

# Get the global key manager
km = get_key_manager()

# Check if keys are available
if km.has_any_key():
    print("Keys available!")
    
# Get a specific key
openai_key = km.get_key("openai")

# See which providers have keys
providers = km.get_available_providers()
```

## Security Best Practices

1. **Use secure methods in production** (OIDC, Service Account, FastAPI)
2. **Never commit API keys to version control**
3. **Rotate keys regularly**
4. **Use HTTPS for all endpoints**
5. **Implement proper access controls**
6. **Monitor and audit key usage**
7. **Use environment variables only for local development**
8. **Encrypt service account files at rest**

## Troubleshooting

### No keys found error

If you see:
```
Error: No LLM API keys found. Required for code summarization.
```

**Check:**
1. Environment variables are set in the current shell
2. Service account file exists and is readable
3. OIDC/FastAPI endpoints are accessible
4. API credentials are valid

**Debug:**
```bash
mdcgen /path/to/repo --log-level DEBUG
```

Look for messages indicating which provider is being tried and why it fails.

### Provider priority issues

If the wrong provider is being used, remember the priority order:
1. FastAPI (highest)
2. Service Account
3. OIDC
4. Environment Variables (lowest)

To force a specific provider, unset the configuration for higher-priority ones.

## Testing

Run the example script to verify your setup:
```bash
python examples/auth_example.py
```

## Support

For issues or questions:
1. Check the documentation in `cursor_mdc_generator/llm_utils/auth/`
2. Review examples in `examples/`
3. Enable debug logging: `--log-level DEBUG`
4. Open an issue on GitHub

## Future Enhancements

Potential additions:
- Azure Key Vault integration
- AWS Systems Manager Parameter Store
- Kubernetes Secrets integration
- Cached key rotation
- Multi-region key distribution
- Key usage analytics

## Changes Summary

**What changed:**
- Added flexible authentication system with 4 methods
- Refactored to use KeyManager for centralized key retrieval
- Enhanced error messages with clear instructions
- Added comprehensive documentation

**What stayed the same:**
- CLI interface and all command-line options
- Environment variable configuration (backward compatible)
- Core functionality of MDC generation
- All existing features

**Benefits:**
- ✅ Enterprise-ready authentication
- ✅ Better security practices
- ✅ Centralized key management
- ✅ Audit and compliance support
- ✅ Flexible deployment options
- ✅ Backward compatible
