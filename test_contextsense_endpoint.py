#!/usr/bin/env python
"""Test the /process_context_sense endpoint locally"""
import requests
import json

# The exact payload from Azure error
payload = {
    "user_id": 10,
    "translated_text": "Haai",
    "source_text": "hey",
    "target_language": "Afrikaans",
    "source_language": "English",
    "core_system_prompt_id": 18,
    "user_audience_id": 225,
    "user_context_id": 200,
    "user_tone_id": 414
}

# Bearer token from your app
bearer_token = "A7x!G2p@Q9#L"

# Test URL (localhost)
url = "http://127.0.0.1:5000/process_context_sense"

# Headers
headers = {
    "Authorization": f"Bearer {bearer_token}",
    "Content-Type": "application/json"
}

print("=" * 80)
print("Testing /process_context_sense endpoint locally")
print("=" * 80)
print(f"\n📍 URL: {url}")
print(f"📦 Payload: {json.dumps(payload, indent=2)}")
print(f"🔐 Bearer Token: {bearer_token}")

try:
    print("\n⏳ Sending POST request...")
    response = requests.post(url, json=payload, headers=headers, timeout=30)
    
    print(f"\n✅ Status Code: {response.status_code}")
    print(f"📋 Response Headers:\n{json.dumps(dict(response.headers), indent=2)}")
    
    try:
        response_json = response.json()
        print(f"\n📊 Response Body:\n{json.dumps(response_json, indent=2)}")
    except:
        print(f"\n📊 Response Body (raw):\n{response.text}")
    
    if response.status_code == 200:
        print("\n✅ SUCCESS! Endpoint is working.")
    else:
        print(f"\n❌ ERROR {response.status_code}")
        if "DeploymentNotFound" in response.text:
            print("   → Deployment not found in Azure OpenAI")
        elif "LLM invocation failed" in response.text:
            print("   → LLM call failed - check Azure endpoint config")
        elif "401" in str(response.status_code):
            print("   → Authentication failed - check bearer token")
            
except requests.exceptions.ConnectionError:
    print("\n❌ ERROR: Cannot connect to http://127.0.0.1:5000")
    print("   → Make sure app is running: python app_with_nosql_routes.py")
except requests.exceptions.Timeout:
    print("\n❌ ERROR: Request timed out (30s)")
except Exception as e:
    print(f"\n❌ ERROR: {type(e).__name__}: {e}")

print("\n" + "=" * 80)
