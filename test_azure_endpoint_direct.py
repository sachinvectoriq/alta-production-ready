#!/usr/bin/env python
"""Direct test to Azure OpenAI endpoint"""
import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

endpoint = os.getenv("Alta_Azure_end_point")
deployment = os.getenv("Alta_deployment_name")
api_key = os.getenv("Azure_Open_api_key")
api_version = os.getenv("Alta_api_version")

print("=" * 80)
print("Direct Azure OpenAI Endpoint Test")
print("=" * 80)
print(f"\n🔹 Endpoint: {endpoint}")
print(f"🔹 Deployment: {deployment}")
print(f"🔹 API Version: {api_version}\n")

# Construct the full URL to hit
url = f"{endpoint}openai/deployments/{deployment}/chat/completions?api-version={api_version}"

print(f"📍 Full URL:\n   {url}\n")

# Simple test message
payload = {
    "messages": [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Say hello"}
    ],
    "temperature": 0,
    "max_tokens": 50
}

headers = {
    "Content-Type": "application/json",
    "api-key": api_key
}

print("⏳ Testing direct connection to Azure OpenAI...")
print(f"   Method: POST")
print(f"   Headers: api-key={api_key[:20]}...")
print(f"   Payload: {json.dumps(payload, indent=2)}\n")

try:
    response = requests.post(url, json=payload, headers=headers, timeout=10)
    
    print(f"✅ Got response! Status Code: {response.status_code}\n")
    
    if response.status_code == 200:
        print("✅ SUCCESS! Deployment is working!")
        print(f"\nResponse:\n{json.dumps(response.json(), indent=2)}")
    else:
        print(f"❌ ERROR Status {response.status_code}")
        print(f"\nResponse:\n{response.text}")
        
        # Parse error
        try:
            error_json = response.json()
            if "error" in error_json:
                error_msg = error_json["error"]
                print(f"\n📌 Error Details:")
                print(f"   Type: {error_msg.get('type')}")
                print(f"   Code: {error_msg.get('code')}")
                print(f"   Message: {error_msg.get('message')}")
        except:
            pass
            
except requests.exceptions.ConnectionError as e:
    print(f"❌ CONNECTION ERROR")
    print(f"   Cannot reach: {endpoint}")
    print(f"   Error: {e}\n")
    print("   💡 Check:")
    print("      - Endpoint URL is correct")
    print("      - No firewall/network blocking")
    print("      - Azure resource is deployed")
    
except requests.exceptions.Timeout as e:
    print(f"❌ TIMEOUT (10 seconds)")
    print(f"   Error: {e}\n")
    print("   💡 This usually means:")
    print("      - Deployment doesn't exist (404 timeout)")
    print("      - Azure credentials invalid (auth timeout)")
    print("      - Network connectivity issue")
    
except Exception as e:
    print(f"❌ ERROR: {type(e).__name__}")
    print(f"   {e}")

print("\n" + "=" * 80)
