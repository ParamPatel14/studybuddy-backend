#!/usr/bin/env python3
"""Test Gemini API connection"""

import os
from dotenv import load_dotenv

load_dotenv()

# Test 1: Check if library is installed
try:
    from google import genai
    print("✓ google-genai library imported successfully")
except ImportError as e:
    print(f"❌ Failed to import google-genai: {e}")
    print("   Install with: pip install google-genai")
    exit(1)

# Test 2: Check API key
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("❌ GEMINI_API_KEY not found in .env")
    exit(1)
elif api_key.startswith("AIzaSy"):
    print(f"✓ API key found: {api_key[:10]}...{api_key[-5:]}")
else:
    print(f"⚠️ API key format seems incorrect: {api_key[:10]}...")

# Test 3: Initialize client
try:
    client = genai.Client(api_key=api_key)
    print("✓ Gemini client initialized")
except Exception as e:
    print(f"❌ Failed to initialize client: {e}")
    exit(1)

# Test 4: List available models
try:
    print("\n📋 Available models:")
    models = client.models.list()
    for model in models:
        print(f"   - {model.name}")
except Exception as e:
    print(f"❌ Failed to list models: {e}")

# Test 5: Simple generation test
try:
    print("\n🧪 Testing simple generation...")
    response = client.models.generate_content(
        model="gemini-2.0-flash-exp",  # Using a more stable model
        contents="Say 'Hello World' in JSON format: {\"message\": \"...\"}"
    )
    
    if response and response.text:
        print(f"✓ Response received: {response.text[:100]}")
    else:
        print("❌ Empty response received")
        
except Exception as e:
    print(f"❌ Generation failed: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*60)
print("✅ Gemini API test complete!")
