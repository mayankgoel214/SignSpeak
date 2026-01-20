"""Quick direct API test"""
import sys
import io
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from openai import OpenAI
import os

# Read directly from .env file
with open('.env', 'r') as f:
    for line in f:
        if line.startswith('OPENAI_API_KEY='):
            api_key = line.strip().split('=', 1)[1]
            break

print(f"Testing API key: {api_key[:20]}...{api_key[-20:]}")
print(f"Key length: {len(api_key)}")

try:
    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "Say hello in one word"}],
        max_tokens=10
    )
    print("\n✅ SUCCESS! API key is valid!")
    print(f"Response: {response.choices[0].message.content}")
except Exception as e:
    print(f"\n❌ ERROR: {e}")
