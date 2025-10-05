# OIDC Authentication Example

This document provides guidance on setting up OIDC authentication for LLM API key management.

## Overview

OIDC (OpenID Connect) authentication allows you to authenticate using an identity provider (IdP) and retrieve API keys from a secure endpoint after authentication.

## Configuration

To use OIDC authentication, you need to configure four environment variables:

```bash
export OIDC_TOKEN_ENDPOINT="https://auth.example.com/oauth/token"
export OIDC_CLIENT_ID="your-client-id"
export OIDC_CLIENT_SECRET="your-client-secret"
export OIDC_KEY_ENDPOINT="https://keys.example.com/api/llm-keys"
```

## Common OIDC Providers

### 1. Keycloak

If you're using Keycloak as your OIDC provider:

```bash
export OIDC_TOKEN_ENDPOINT="https://keycloak.example.com/realms/your-realm/protocol/openid-connect/token"
export OIDC_CLIENT_ID="mdcgen-client"
export OIDC_CLIENT_SECRET="client-secret-from-keycloak"
export OIDC_KEY_ENDPOINT="https://your-api.example.com/api/llm-keys"
```

#### Keycloak Setup:

1. Create a new client in Keycloak
2. Set "Access Type" to "confidential"
3. Enable "Service Accounts Enabled"
4. Save and note the client secret from the "Credentials" tab

### 2. Auth0

If you're using Auth0:

```bash
export OIDC_TOKEN_ENDPOINT="https://your-tenant.auth0.com/oauth/token"
export OIDC_CLIENT_ID="your-client-id"
export OIDC_CLIENT_SECRET="your-client-secret"
export OIDC_KEY_ENDPOINT="https://your-api.example.com/api/llm-keys"
```

#### Auth0 Setup:

1. Create a new application (Machine to Machine)
2. Select the API you want to authorize
3. Note the Client ID and Client Secret

### 3. Okta

If you're using Okta:

```bash
export OIDC_TOKEN_ENDPOINT="https://your-domain.okta.com/oauth2/default/v1/token"
export OIDC_CLIENT_ID="your-client-id"
export OIDC_CLIENT_SECRET="your-client-secret"
export OIDC_KEY_ENDPOINT="https://your-api.example.com/api/llm-keys"
```

#### Okta Setup:

1. Create a new application (Web application)
2. Enable "Client Credentials" grant type
3. Note the Client ID and Client Secret

### 4. Azure AD

If you're using Azure Active Directory:

```bash
export OIDC_TOKEN_ENDPOINT="https://login.microsoftonline.com/your-tenant-id/oauth2/v2.0/token"
export OIDC_CLIENT_ID="your-application-id"
export OIDC_CLIENT_SECRET="your-client-secret"
export OIDC_KEY_ENDPOINT="https://your-api.example.com/api/llm-keys"
```

#### Azure AD Setup:

1. Register a new application in Azure Portal
2. Create a client secret
3. Grant necessary API permissions

## Key Endpoint Implementation

Your key endpoint should:

1. Validate the access token from the OIDC provider
2. Return LLM API keys in JSON format

### Example Key Endpoint (FastAPI)

```python
from fastapi import FastAPI, Depends, HTTPException, Header
from typing import Optional
import jwt
from jwt import PyJWKClient
import os

app = FastAPI()

# Configure JWT validation (example for Keycloak)
JWKS_URL = "https://keycloak.example.com/realms/your-realm/protocol/openid-connect/certs"
jwks_client = PyJWKClient(JWKS_URL)

def verify_token(authorization: Optional[str] = Header(None)):
    """Verify the JWT token from the Authorization header."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")
    
    token = authorization.split(" ")[1]
    
    try:
        # Get the signing key from the JWKS endpoint
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        
        # Decode and validate the token
        decoded = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience="your-audience",
            options={"verify_exp": True}
        )
        return decoded
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Token validation failed: {str(e)}")

@app.get("/api/llm-keys")
async def get_llm_keys(user: dict = Depends(verify_token)):
    """
    Get LLM API keys for authenticated users.
    
    The token from OIDC authentication is validated, and keys are returned.
    """
    # In production, retrieve these from a secrets management system
    return {
        "openai": os.getenv("OPENAI_API_KEY", ""),
        "anthropic": os.getenv("ANTHROPIC_API_KEY", ""),
        "gemini": os.getenv("GEMINI_API_KEY", ""),
        "deepseek": os.getenv("DEEPSEEK_API_KEY", ""),
    }
```

## Authentication Flow

1. **mdcgen starts** and detects OIDC configuration
2. **mdcgen authenticates** with the OIDC provider using client credentials
3. **OIDC provider returns** an access token
4. **mdcgen uses the token** to request API keys from the key endpoint
5. **Key endpoint validates** the token and returns the keys
6. **mdcgen uses the keys** for LLM API calls

## Security Considerations

### 1. Token Storage

The access token is kept in memory and not persisted to disk.

### 2. Token Expiration

Tokens typically expire after a short period. If token expiration occurs during execution, mdcgen will re-authenticate.

### 3. Scopes and Permissions

Configure your OIDC client with minimal necessary scopes:

```bash
# Example for specific scopes
export OIDC_SCOPE="read:llm-keys"
```

### 4. Network Security

- Always use HTTPS for all endpoints
- Consider using mutual TLS for additional security
- Implement network-level access controls (VPN, IP whitelisting)

## Troubleshooting

### Authentication Fails

Enable debug logging to see detailed error messages:

```bash
mdcgen /path/to/repo --log-level DEBUG
```

Look for messages like:
```
ERROR - OIDC authentication failed: ...
```

### Common Issues

1. **Invalid client credentials**: Verify OIDC_CLIENT_ID and OIDC_CLIENT_SECRET
2. **Wrong token endpoint**: Verify the OIDC_TOKEN_ENDPOINT URL
3. **Network connectivity**: Ensure the endpoints are accessible
4. **Token validation fails**: Check if the key endpoint is properly validating tokens

### Testing OIDC Configuration

Test your OIDC configuration manually:

```bash
# Get access token
curl -X POST "$OIDC_TOKEN_ENDPOINT" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials" \
  -d "client_id=$OIDC_CLIENT_ID" \
  -d "client_secret=$OIDC_CLIENT_SECRET"

# Use the token to get keys
curl -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  "$OIDC_KEY_ENDPOINT"
```

## Example: Complete Setup with Keycloak

1. **Set up Keycloak** (docker-compose.yml):

```yaml
version: '3'
services:
  keycloak:
    image: quay.io/keycloak/keycloak:latest
    environment:
      KEYCLOAK_ADMIN: admin
      KEYCLOAK_ADMIN_PASSWORD: admin
    ports:
      - "8080:8080"
    command: start-dev
```

2. **Create client in Keycloak**:
   - Login to Keycloak admin console
   - Create a new client "mdcgen-client"
   - Enable "Service Accounts Enabled"
   - Note the client secret

3. **Deploy key endpoint**:

```python
# key_service.py
from fastapi import FastAPI, Depends
import os

app = FastAPI()

# Your token verification logic here
@app.get("/api/llm-keys")
async def get_llm_keys():
    return {
        "openai": os.getenv("OPENAI_API_KEY"),
        # ... other keys
    }
```

4. **Configure mdcgen**:

```bash
export OIDC_TOKEN_ENDPOINT="http://localhost:8080/realms/master/protocol/openid-connect/token"
export OIDC_CLIENT_ID="mdcgen-client"
export OIDC_CLIENT_SECRET="your-client-secret"
export OIDC_KEY_ENDPOINT="http://localhost:8000/api/llm-keys"

mdcgen /path/to/repo
```

## Benefits of OIDC Authentication

1. **Centralized authentication** - Use your existing identity provider
2. **Better security** - Credentials are not stored in environment variables
3. **Audit trail** - OIDC providers log all authentication attempts
4. **Token expiration** - Automatic security through short-lived tokens
5. **Integration** - Works with existing enterprise identity systems
