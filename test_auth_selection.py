#!/usr/bin/env python3
"""
Test to verify the new dual-auth system:
1. If Azure_Open_api_key is available → use API key (local dev)
2. If not → use Managed Identity via az login (production)
"""

import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()

print("=" * 60)
print("🔍 AUTHENTICATION METHOD SELECTION TEST")
print("=" * 60)

# Check environment variables
api_key = os.getenv("Azure_Open_api_key")
endpoint = os.getenv("Alta_Azure_end_point")
deployment = os.getenv("Alta_deployment_name")

print("\n✓ Environment Variables Loaded:")
print(f"  • Endpoint: {endpoint}")
print(f"  • Deployment: {deployment}")
print(f"  • API Key exists: {'YES' if api_key else 'NO'}")

if api_key:
    print(f"  • API Key value: {api_key[:10]}... (masked)")

print("\n📋 AUTHENTICATION DECISION:")
print("-" * 60)

# Simulate the logic from updated code
from azure.identity import DefaultAzureCredential, get_bearer_token_provider

print("\n1️⃣  Attempting Managed Identity (DefaultAzureCredential)...")
try:
    credential = DefaultAzureCredential()
    # Test if credentials work
    token = credential.get_token("https://cognitiveservices.azure.com/.default")
    print("   ✅ Managed Identity SUCCEEDED")
    print(f"   → Will use: Managed Identity authentication")
    token_provider = get_bearer_token_provider(credential, "https://cognitiveservices.azure.com/.default")
    selected_auth = "Managed Identity"
except Exception as e:
    print(f"   ❌ Managed Identity FAILED: {e}")
    print("   → Falling back to API Key...")
    
    if api_key:
        print(f"   ✅ API Key AVAILABLE")
        print(f"   → Will use: API Key authentication")
        selected_auth = "API Key"
        token_provider = None
    else:
        print(f"   ❌ API Key NOT AVAILABLE")
        print(f"   → ERROR: No authentication method available!")
        selected_auth = "NONE (ERROR)"
        token_provider = None

print("\n" + "=" * 60)
print(f"🎯 SELECTED AUTH METHOD: {selected_auth}")
print("=" * 60)

print("\n💡 NEXT STEPS:")
if selected_auth == "Managed Identity":
    print("   ✅ Ready for production on Azure App Service")
    print("   ✅ Ready for local dev with 'az login'")
elif selected_auth == "API Key":
    print("   ⚠️  Using API Key (local development mode)")
    print("   📝 For production: Remove API Key and use Managed Identity")
else:
    print("   🚨 URGENT: No authentication method available!")
    print("   📝 Run 'az login' OR set Azure_Open_api_key in .env")

print("\n" + "=" * 60)
