"""
Diagnostic script to test Azure OpenAI configuration.
Run this to verify the endpoint, deployment, and authentication are correct.
"""

import os
from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from langchain_openai import AzureChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

load_dotenv()

print("=" * 60)
print("Azure OpenAI Configuration Diagnostic")
print("=" * 60)

# 1. Check environment variables
print("\n1. Checking Environment Variables:")
endpoint = os.getenv("Alta_Azure_end_point")
deployment = os.getenv("Alta_deployment_name")
api_version = os.getenv("Alta_api_version")

print(f"   Endpoint: {endpoint}")
print(f"   Deployment: {deployment}")
print(f"   API Version: {api_version}")

if not all([endpoint, deployment, api_version]):
    print("   ❌ ERROR: Missing required environment variables!")
    exit(1)

if endpoint.endswith("/"):
    print("   ⚠️  WARNING: Endpoint has trailing slash (should remove)")
else:
    print("   ✅ Endpoint format looks good (no trailing slash)")

# 2. Test credentials
print("\n2. Testing Azure Credentials:")
try:
    credential = DefaultAzureCredential()
    print("   ✅ DefaultAzureCredential initialized successfully")
except Exception as e:
    print(f"   ❌ ERROR: Failed to create credentials: {e}")
    exit(1)

# 3. Test token provider
print("\n3. Testing Bearer Token Provider:")
try:
    token_provider = get_bearer_token_provider(
        credential, "https://cognitiveservices.azure.com/.default"
    )
    print("   ✅ Token provider created successfully")
except Exception as e:
    print(f"   ❌ ERROR: Failed to create token provider: {e}")
    exit(1)

# 4. Test Azure OpenAI connection
print("\n4. Testing Azure OpenAI Connection:")
try:
    llm = AzureChatOpenAI(
        deployment_name=deployment,
        model="gpt-5.1",
        temperature=0,
        azure_ad_token_provider=token_provider,
        azure_endpoint=endpoint,
        openai_api_version=api_version
    )
    print("   ✅ AzureChatOpenAI client created successfully")
except Exception as e:
    print(f"   ❌ ERROR: Failed to create AzureChatOpenAI: {e}")
    exit(1)

# 5. Test LLM invocation
print("\n5. Testing LLM Invocation:")
try:
    messages = [
        SystemMessage(content="You are a helpful assistant."),
        HumanMessage(content="Hello, are you working?")
    ]
    response = llm.invoke(messages)
    print(f"   ✅ LLM invocation successful!")
    print(f"   Response: {response.content[:100]}...")
except Exception as e:
    print(f"   ❌ ERROR: LLM invocation failed: {e}")
    exit(1)

print("\n" + "=" * 60)
print("✅ All configuration tests passed!")
print("=" * 60)
