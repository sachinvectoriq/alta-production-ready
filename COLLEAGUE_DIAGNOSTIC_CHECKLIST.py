#!/usr/bin/env python3
"""
DIAGNOSTIC CHECKLIST FOR COLLEAGUE

The deployed app is getting: DeploymentNotFound
This means the deployment doesn't exist in the specified resource.

Your colleague MUST verify these 3 things in Azure Portal:
"""

print("""
================================================================================
🚨 DIAGNOSTIC CHECKLIST - DeploymentNotFound Error
================================================================================

Current .env Configuration:
  ✅ Endpoint: https://aif-alta-qa-001.cognitiveservices.azure.com/
  ✅ Deployment: gpt-5.1
  ✅ API Version: 2025-04-01-preview

Error from Deployed App:
  ❌ DeploymentNotFound: "The API deployment for this resource does not exist"

================================================================================
COLLEAGUE MUST CHECK (in Azure Portal):
================================================================================

1️⃣  VERIFY RESOURCE EXISTS
   Go to: Azure Portal → Search "aif-alta-qa-001"
   
   ✓ Is there a Cognitive Services resource named "aif-alta-qa-001"?
     YES → Continue to step 2
     NO  → ❌ RESOURCE DOESN'T EXIST! Use wrong endpoint in .env

2️⃣  VERIFY DEPLOYMENT EXISTS IN RESOURCE
   Go to: Resource "aif-alta-qa-001" → Model Deployments
   
   ✓ Do you see a deployment named "gpt-5.1"?
     
     If NO deployments exist:
       → Go to "Deploy Model"
       → Create deployment named "gpt-5.1" with appropriate model
       → Wait for deployment status = "Succeeded"
   
     If different deployment names exist:
       → Update .env with the CORRECT deployment name
       → Example: If you see "gpt-4o", change .env to:
          Alta_deployment_name=gpt-4o

3️⃣  VERIFY DEPLOYMENT STATUS
   Go to: Resource "aif-alta-qa-001" → Model Deployments
   
   ✓ Find deployment "gpt-5.1" and check status:
     Status = "Succeeded" → ✅ OK
     Status = "Creating"  → ⏳ Wait 5+ minutes, then retry
     Status = "Failed"    → ❌ Delete and recreate deployment

================================================================================
📋 WHAT TO SEND BACK:
================================================================================

Once you verify, please provide:

1. ✅ Resource "aif-alta-qa-001" EXISTS: YES / NO
2. ✅ Deployment exists in that resource: 
      - List of ALL deployments visible in Portal
      - Example: ["gpt-5.1", "gpt-4o", "other-model"]
3. ✅ Correct deployment name for .env:
      - Example: "gpt-5.1" OR "gpt-4o" OR "something-else"
4. ✅ Deployment Status (Succeeded/Creating/Failed)

================================================================================
IF UNSURE WHICH DEPLOYMENT TO USE:
================================================================================

Run this command in Azure CLI (colleague must do this):

  az cognitiveservices account deployment list \\
    --resource-group <your-resource-group> \\
    --name aif-alta-qa-001

This will show ALL deployments in the resource.
Copy the exact "name" field from the output.

================================================================================
""")
