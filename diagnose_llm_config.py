#!/usr/bin/env python
"""Diagnose Azure OpenAI LLM configuration"""
import os
from dotenv import load_dotenv
import json

load_dotenv()

print("=" * 80)
print("Azure OpenAI Configuration Check")
print("=" * 80)

# Check environment variables
endpoint = os.getenv("Alta_Azure_end_point")
deployment = os.getenv("Alta_deployment_name")
api_key = os.getenv("Azure_Open_api_key")
api_version = os.getenv("Alta_api_version")

print(f"\n🔹 Endpoint: {endpoint}")
print(f"🔹 Deployment: {deployment}")
print(f"🔹 API Version: {api_version}")
print(f"🔹 API Key (truncated): {api_key[:20]}..." if api_key else "🔹 API Key: NOT SET")

# Validate format
print("\n✓ Configuration Validation:")
issues = []

if not endpoint:
    issues.append("  ❌ Alta_Azure_end_point is missing")
elif not endpoint.endswith("/"):
    issues.append("  ⚠️  Alta_Azure_end_point should end with /")
else:
    print("  ✅ Endpoint URL format OK")

if not deployment:
    issues.append("  ❌ Alta_deployment_name is missing")
else:
    print(f"  ✅ Deployment name set: {deployment}")

if not api_key:
    issues.append("  ❌ Azure_Open_api_key is missing")
else:
    print("  ✅ API Key present")

if not api_version:
    issues.append("  ❌ Alta_api_version is missing")
else:
    print(f"  ✅ API version set: {api_version}")

if issues:
    print("\n⚠️  Issues found:")
    for issue in issues:
        print(issue)
else:
    print("\n✅ All configuration looks correct!")

# Try to import langchain LLM
print("\n" + "=" * 80)
print("Testing LLM Import")
print("=" * 80)

try:
    from langchain_openai import AzureChatOpenAI
    from azure.identity import DefaultAzureCredential, get_bearer_token_for_user
    
    print("\n✅ LangChain and Azure Identity imports successful")
    
    print("\n⏳ Attempting to create LLM client...")
    
    # Create token provider
    from azure.identity import DefaultAzureCredential
    credential = DefaultAzureCredential()
    token_provider = lambda: credential.get_token("https://cognitiveservices.azure.com/.default").token
    
    llm = AzureChatOpenAI(
        deployment_name=deployment,
        model="gpt-5.1",
        temperature=0,
        azure_ad_token_provider=token_provider,
        azure_endpoint=endpoint,
        openai_api_version=api_version
    )
    
    print("✅ LLM client created successfully!")
    print("\n💡 Try a simple invoke to test the connection:")
    print('   llm.invoke([{"role": "user", "content": "Hello"}])')
    
except ImportError as e:
    print(f"❌ Import Error: {e}")
except Exception as e:
    print(f"❌ LLM Creation Error: {e}")
    print("\n💡 Common causes:")
    print("   - Invalid Azure endpoint URL")
    print("   - Deployment doesn't exist")
    print("   - Azure credentials not configured")
    print("   - API key/token expired")

print("\n" + "=" * 80)
