# Examples

This directory contains example scripts demonstrating various features of mdcgen.

## Authentication Example

`auth_example.py` - Demonstrates how to use the authentication system programmatically.

### Running the example:

```bash
# With environment variables
export OPENAI_API_KEY="sk-..."
python examples/auth_example.py

# Without keys (shows how to handle missing keys)
python examples/auth_example.py
```

### What it demonstrates:

1. Using the default key manager
2. Getting specific API keys
3. Creating custom key managers with specific providers
4. Setting custom key managers globally
5. Checking provider availability

## More Examples

For more detailed examples and use cases, see the authentication documentation:

- [Authentication Overview](../cursor_mdc_generator/llm_utils/auth/README.md)
- [FastAPI Service Example](../cursor_mdc_generator/llm_utils/auth/FASTAPI_EXAMPLE.md)
- [OIDC Setup Guide](../cursor_mdc_generator/llm_utils/auth/OIDC_EXAMPLE.md)
- [Service Account Guide](../cursor_mdc_generator/llm_utils/auth/SERVICE_ACCOUNT_EXAMPLE.md)
