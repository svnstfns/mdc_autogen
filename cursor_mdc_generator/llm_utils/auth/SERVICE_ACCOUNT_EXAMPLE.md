# Service Account Authentication Example

This document provides guidance on setting up Service Account authentication for LLM API key management.

## Overview

Service Account authentication allows you to use a service account credentials file to authenticate and retrieve API keys from a secure endpoint.

## Configuration

To use Service Account authentication, you need to configure two environment variables:

```bash
export SERVICE_ACCOUNT_FILE="/path/to/service-account.json"
export SERVICE_ACCOUNT_KEY_ENDPOINT="https://keys.example.com/api/llm-keys"
```

## Service Account File Format

The service account file should be a JSON file with the following structure:

```json
{
  "client_id": "service-account-id",
  "token": "service-account-token",
  "api_key": "service-account-api-key",
  "type": "service_account",
  "project_id": "your-project",
  "created_at": "2024-01-01T00:00:00Z"
}
```

### Required Fields

- `client_id`: The service account identifier
- `token` or `api_key`: The authentication credential (at least one is required)

### Optional Fields

- `type`: Type of service account (for documentation)
- `project_id`: Associated project identifier
- `created_at`: Timestamp of creation

## Example Implementations

### 1. Simple Token-Based Authentication

#### Service Account File:

```json
{
  "client_id": "mdcgen-service",
  "token": "sa-token-abc123xyz",
  "type": "service_account"
}
```

#### Key Endpoint (FastAPI):

```python
from fastapi import FastAPI, Header, HTTPException
from typing import Optional
import os

app = FastAPI()

# In production, store these in a database
VALID_SERVICE_ACCOUNTS = {
    "sa-token-abc123xyz": "mdcgen-service"
}

def verify_service_account(
    authorization: Optional[str] = Header(None),
    x_service_account: Optional[str] = Header(None)
):
    """Verify service account credentials."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing authorization header")
    
    token = authorization.split(" ")[1]
    
    if token not in VALID_SERVICE_ACCOUNTS:
        raise HTTPException(status_code=401, detail="Invalid service account token")
    
    return VALID_SERVICE_ACCOUNTS[token]

@app.get("/api/llm-keys")
async def get_llm_keys(service_account: str = Depends(verify_service_account)):
    """Get LLM API keys for authenticated service account."""
    return {
        "openai": os.getenv("OPENAI_API_KEY", ""),
        "anthropic": os.getenv("ANTHROPIC_API_KEY", ""),
        "gemini": os.getenv("GEMINI_API_KEY", ""),
        "deepseek": os.getenv("DEEPSEEK_API_KEY", ""),
    }
```

### 2. Google Cloud-Style Service Account

#### Service Account File (Google Cloud format):

```json
{
  "type": "service_account",
  "project_id": "my-project",
  "private_key_id": "key-id-123",
  "private_key": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n",
  "client_email": "mdcgen@my-project.iam.gserviceaccount.com",
  "client_id": "1234567890",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/..."
}
```

#### Using with Google Cloud Secret Manager:

```python
from google.cloud import secretmanager
from google.oauth2 import service_account
import json

def get_keys_from_gcp(service_account_file: str) -> dict:
    """Get LLM API keys from Google Cloud Secret Manager."""
    
    # Load service account credentials
    credentials = service_account.Credentials.from_service_account_file(
        service_account_file
    )
    
    # Create Secret Manager client
    client = secretmanager.SecretManagerServiceClient(credentials=credentials)
    
    project_id = json.load(open(service_account_file))['project_id']
    
    # Retrieve secrets
    keys = {}
    for provider in ['openai', 'anthropic', 'gemini', 'deepseek']:
        secret_name = f"llm-{provider}-key"
        name = f"projects/{project_id}/secrets/{secret_name}/versions/latest"
        
        try:
            response = client.access_secret_version(request={"name": name})
            keys[provider] = response.payload.data.decode('UTF-8')
        except Exception as e:
            print(f"Failed to get {provider} key: {e}")
    
    return keys
```

### 3. AWS-Style Service Account

#### Service Account File (AWS format):

```json
{
  "client_id": "AKIA...",
  "api_key": "aws-secret-access-key",
  "region": "us-east-1",
  "type": "aws_iam"
}
```

#### Using with AWS Secrets Manager:

```python
import boto3
import json

def get_keys_from_aws(service_account_file: str) -> dict:
    """Get LLM API keys from AWS Secrets Manager."""
    
    # Load service account credentials
    with open(service_account_file) as f:
        credentials = json.load(f)
    
    # Create Secrets Manager client
    session = boto3.Session(
        aws_access_key_id=credentials['client_id'],
        aws_secret_access_key=credentials['api_key'],
        region_name=credentials.get('region', 'us-east-1')
    )
    client = session.client('secretsmanager')
    
    # Retrieve secrets
    try:
        response = client.get_secret_value(SecretId='llm-api-keys')
        return json.loads(response['SecretString'])
    except Exception as e:
        print(f"Failed to get secrets: {e}")
        return {}
```

### 4. HashiCorp Vault-Style Service Account

#### Service Account File:

```json
{
  "client_id": "mdcgen-role",
  "token": "hvs.CAESIJ...",
  "vault_addr": "https://vault.example.com",
  "type": "vault"
}
```

#### Using with HashiCorp Vault:

```python
import hvac
import json

def get_keys_from_vault(service_account_file: str) -> dict:
    """Get LLM API keys from HashiCorp Vault."""
    
    # Load service account credentials
    with open(service_account_file) as f:
        credentials = json.load(f)
    
    # Create Vault client
    client = hvac.Client(
        url=credentials['vault_addr'],
        token=credentials['token']
    )
    
    # Read secrets
    try:
        secret = client.secrets.kv.v2.read_secret_version(
            path='llm-api-keys',
            mount_point='secret'
        )
        return secret['data']['data']
    except Exception as e:
        print(f"Failed to read from Vault: {e}")
        return {}
```

## Creating a Service Account File

### Manual Creation

Create a JSON file with your credentials:

```bash
cat > service-account.json << EOF
{
  "client_id": "mdcgen-service",
  "token": "$(openssl rand -hex 32)",
  "type": "service_account",
  "created_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
EOF

chmod 600 service-account.json
```

### Using a Script

```python
#!/usr/bin/env python3
"""Generate a service account file."""

import json
import secrets
import sys
from datetime import datetime

def generate_service_account(client_id: str, output_file: str):
    """Generate a service account credentials file."""
    
    service_account = {
        "client_id": client_id,
        "token": secrets.token_hex(32),
        "type": "service_account",
        "created_at": datetime.utcnow().isoformat() + "Z"
    }
    
    with open(output_file, 'w') as f:
        json.dump(service_account, f, indent=2)
    
    print(f"Service account created: {output_file}")
    print(f"Client ID: {service_account['client_id']}")
    print(f"Token: {service_account['token']}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: generate_sa.py <client_id> <output_file>")
        sys.exit(1)
    
    generate_service_account(sys.argv[1], sys.argv[2])
```

Usage:
```bash
python generate_sa.py mdcgen-service service-account.json
```

## Configuration Example

### Full Setup

1. **Create service account file:**

```bash
python generate_sa.py mdcgen-prod sa-prod.json
```

2. **Register the service account** with your key management service

3. **Configure mdcgen:**

```bash
export SERVICE_ACCOUNT_FILE="/secure/path/sa-prod.json"
export SERVICE_ACCOUNT_KEY_ENDPOINT="https://keys.example.com/api/llm-keys"
mdcgen /path/to/repo
```

### Docker Setup

```dockerfile
FROM python:3.9-slim

WORKDIR /app

# Copy service account file
COPY service-account.json /app/config/

ENV SERVICE_ACCOUNT_FILE=/app/config/service-account.json
ENV SERVICE_ACCOUNT_KEY_ENDPOINT=https://keys.example.com/api/llm-keys

RUN pip install mdcgen

ENTRYPOINT ["mdcgen"]
```

### Kubernetes Setup

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: mdcgen-service-account
type: Opaque
stringData:
  service-account.json: |
    {
      "client_id": "mdcgen-k8s",
      "token": "your-token-here"
    }

---
apiVersion: v1
kind: Pod
metadata:
  name: mdcgen
spec:
  containers:
  - name: mdcgen
    image: mdcgen:latest
    env:
    - name: SERVICE_ACCOUNT_FILE
      value: /config/service-account.json
    - name: SERVICE_ACCOUNT_KEY_ENDPOINT
      value: https://keys.example.com/api/llm-keys
    volumeMounts:
    - name: sa-config
      mountPath: /config
      readOnly: true
  volumes:
  - name: sa-config
    secret:
      secretName: mdcgen-service-account
```

## Security Best Practices

1. **File Permissions**: Set restrictive permissions on service account files
   ```bash
   chmod 600 service-account.json
   ```

2. **Rotation**: Rotate service account credentials regularly
   ```bash
   # Rotate every 90 days
   0 0 1 */3 * /usr/local/bin/rotate_service_account.sh
   ```

3. **Auditing**: Log all service account usage
   ```python
   logging.info(f"Service account {client_id} accessed keys at {timestamp}")
   ```

4. **Encryption**: Encrypt service account files at rest
   ```bash
   # Encrypt with GPG
   gpg --symmetric --cipher-algo AES256 service-account.json
   ```

5. **Secrets Management**: Use a dedicated secrets management system

6. **Least Privilege**: Grant only necessary permissions

7. **Monitoring**: Alert on unusual service account activity

## Troubleshooting

### Service Account File Not Found

```bash
# Verify file exists
ls -l "$SERVICE_ACCOUNT_FILE"

# Check permissions
ls -la "$SERVICE_ACCOUNT_FILE"
```

### Authentication Fails

Enable debug logging:
```bash
mdcgen /path/to/repo --log-level DEBUG
```

Look for:
```
ERROR - Service account file not found: ...
ERROR - Failed to load service account file: ...
ERROR - Failed to fetch keys using service account: ...
```

### Testing Service Account

```bash
# Test the endpoint manually
TOKEN=$(jq -r .token service-account.json)
CLIENT_ID=$(jq -r .client_id service-account.json)

curl -H "Authorization: Bearer $TOKEN" \
     -H "X-Service-Account: $CLIENT_ID" \
     "$SERVICE_ACCOUNT_KEY_ENDPOINT"
```

## Migration from Environment Variables

To migrate from environment variables to service accounts:

1. **Create service account:**
   ```bash
   python generate_sa.py myapp-prod sa.json
   ```

2. **Register with key service**

3. **Test configuration:**
   ```bash
   export SERVICE_ACCOUNT_FILE=sa.json
   export SERVICE_ACCOUNT_KEY_ENDPOINT=https://keys.example.com/api/llm-keys
   mdcgen /path/to/repo --log-level DEBUG
   ```

4. **Remove environment variables:**
   ```bash
   unset OPENAI_API_KEY ANTHROPIC_API_KEY GEMINI_API_KEY DEEPSEEK_API_KEY
   ```

5. **Verify it works:**
   ```bash
   mdcgen /path/to/repo
   ```
