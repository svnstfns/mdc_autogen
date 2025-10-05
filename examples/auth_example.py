#!/usr/bin/env python3
"""
Example demonstrating how to use the authentication system programmatically.

This example shows how to:
1. Use the default key manager
2. Create a custom key manager with specific providers
3. Check for available keys
4. Retrieve keys for specific providers
"""

from cursor_mdc_generator.llm_utils.auth import (
    KeyManager,
    EnvironmentKeyProvider,
    FastAPIKeyProvider,
    get_key_manager,
    set_key_manager,
)

print("Authentication System Example")
print("=" * 60)

# Example 1: Using the default key manager
print("\n1. Using the default key manager:")
print("-" * 60)
km = get_key_manager()
print(f"Has any API key available: {km.has_any_key()}")
print(f"Available providers: {km.get_available_providers()}")

# Example 2: Getting a specific key
print("\n2. Getting a specific API key:")
print("-" * 60)
openai_key = km.get_key("openai")
if openai_key:
    print(f"OpenAI key found: {openai_key[:10]}...")
else:
    print("OpenAI key not found")

# Example 3: Creating a custom key manager
print("\n3. Creating a custom key manager:")
print("-" * 60)
custom_km = KeyManager(
    providers=[
        FastAPIKeyProvider(api_endpoint="https://api.example.com"),
        EnvironmentKeyProvider(),  # Fallback to environment variables
    ]
)
print("Custom key manager created with:")
print("  - FastAPI provider (priority 1)")
print("  - Environment variable provider (priority 2)")

# Example 4: Setting a custom key manager globally
print("\n4. Setting custom key manager globally:")
print("-" * 60)
set_key_manager(custom_km)
new_km = get_key_manager()
print(f"Global key manager updated: {new_km is custom_km}")

# Example 5: Checking availability of individual providers
print("\n5. Checking individual provider availability:")
print("-" * 60)
env_provider = EnvironmentKeyProvider()
print(f"Environment provider available: {env_provider.is_available()}")

fastapi_provider = FastAPIKeyProvider(api_endpoint="https://api.example.com")
print(f"FastAPI provider configured: {fastapi_provider.is_available()}")

print("\n" + "=" * 60)
print("Example completed!")
print("\nFor more information, see:")
print("  - cursor_mdc_generator/llm_utils/auth/README.md")
print("  - cursor_mdc_generator/llm_utils/auth/FASTAPI_EXAMPLE.md")
print("  - cursor_mdc_generator/llm_utils/auth/OIDC_EXAMPLE.md")
print("  - cursor_mdc_generator/llm_utils/auth/SERVICE_ACCOUNT_EXAMPLE.md")
