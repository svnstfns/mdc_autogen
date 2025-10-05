# FastAPI Key Management Service Example

This document provides an example implementation of a FastAPI service for managing LLM API keys.

## Example FastAPI Service

Here's a simple example of a FastAPI service that provides LLM API keys:

```python
from fastapi import FastAPI, Header, HTTPException, Depends
from typing import Optional, Dict
import os

app = FastAPI(title="LLM Key Management Service")

# Simple API key authentication
API_KEY = os.getenv("SERVICE_API_KEY", "your-secret-api-key")


def verify_api_key(x_api_key: Optional[str] = Header(None)):
    """Verify the API key from the request header."""
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return x_api_key


@app.get("/llm-keys")
async def get_llm_keys(api_key: str = Depends(verify_api_key)) -> Dict[str, str]:
    """
    Get LLM API keys for all providers.
    
    This endpoint returns API keys for various LLM providers.
    In a production environment, these would be retrieved from a secure
    secrets management system (e.g., HashiCorp Vault, AWS Secrets Manager).
    """
    return {
        "openai": os.getenv("OPENAI_API_KEY", ""),
        "anthropic": os.getenv("ANTHROPIC_API_KEY", ""),
        "gemini": os.getenv("GEMINI_API_KEY", ""),
        "deepseek": os.getenv("DEEPSEEK_API_KEY", ""),
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

## Running the Service

### Install dependencies:

```bash
pip install fastapi uvicorn
```

### Set environment variables:

```bash
export SERVICE_API_KEY="your-secure-api-key"
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-ant-..."
```

### Run the service:

```bash
python key_service.py
# or
uvicorn key_service:app --host 0.0.0.0 --port 8000
```

## Using the Service with mdcgen

Once your FastAPI service is running, configure mdcgen to use it:

```bash
export FASTAPI_KEY_ENDPOINT="http://localhost:8000"
export FASTAPI_API_KEY="your-secure-api-key"
mdcgen /path/to/repo
```

## Production Deployment

For production deployments, consider:

### 1. Using a Secrets Management System

```python
from fastapi import FastAPI
import boto3
import json

app = FastAPI()

def get_secrets_from_aws():
    """Retrieve secrets from AWS Secrets Manager."""
    client = boto3.client('secretsmanager')
    response = client.get_secret_value(SecretId='llm-api-keys')
    return json.loads(response['SecretString'])

@app.get("/llm-keys")
async def get_llm_keys():
    return get_secrets_from_aws()
```

### 2. Adding HTTPS/TLS

```bash
uvicorn key_service:app --host 0.0.0.0 --port 8443 \
  --ssl-keyfile=/path/to/key.pem \
  --ssl-certfile=/path/to/cert.pem
```

### 3. Adding Rate Limiting

```python
from fastapi import FastAPI
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app = FastAPI()
app.state.limiter = limiter
app.add_exception_handler(429, _rate_limit_exceeded_handler)

@app.get("/llm-keys")
@limiter.limit("10/minute")
async def get_llm_keys(request: Request):
    # ... your code
```

### 4. Adding Authentication with OAuth2

```python
from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer

app = FastAPI()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

async def get_current_user(token: str = Depends(oauth2_scheme)):
    # Validate token and return user
    # This is a simplified example
    if not validate_token(token):
        raise HTTPException(status_code=401, detail="Invalid token")
    return {"username": "user"}

@app.get("/llm-keys")
async def get_llm_keys(current_user: dict = Depends(get_current_user)):
    # Return keys for authenticated user
    pass
```

### 5. Docker Deployment

Create a `Dockerfile`:

```dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY key_service.py .

EXPOSE 8000

CMD ["uvicorn", "key_service:app", "--host", "0.0.0.0", "--port", "8000"]
```

Build and run:

```bash
docker build -t llm-key-service .
docker run -p 8000:8000 \
  -e SERVICE_API_KEY="your-key" \
  -e OPENAI_API_KEY="sk-..." \
  llm-key-service
```

## Security Best Practices

1. **Always use HTTPS in production**
2. **Implement proper authentication** (API keys, OAuth2, JWT)
3. **Use a secrets management system** (Vault, AWS Secrets Manager, etc.)
4. **Add rate limiting** to prevent abuse
5. **Log all access attempts** for auditing
6. **Rotate API keys regularly**
7. **Use environment-specific configurations**
8. **Implement IP whitelisting** if possible
9. **Monitor and alert on unusual access patterns**
10. **Keep dependencies up to date**

## Testing the Service

```bash
# Health check
curl http://localhost:8000/health

# Get keys (with authentication)
curl -H "X-API-Key: your-secure-api-key" http://localhost:8000/llm-keys
```

Expected response:
```json
{
  "openai": "sk-...",
  "anthropic": "sk-ant-...",
  "gemini": "...",
  "deepseek": "..."
}
```
