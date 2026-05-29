import os
from dotenv import load_dotenv
from huggingface_hub import InferenceClient

load_dotenv()

HF_TOKEN = os.getenv("HF_TOKEN")
# Testing the exact model that is failing
TEST_MODEL = "Qwen/Qwen3.6-35B-A3B"

print(f"🔄 Sending request to {TEST_MODEL}...")

client = InferenceClient(model=TEST_MODEL, token=HF_TOKEN, timeout=60)

# A fake prompt similar to what your router sends
test_prompt = """
You are a Triage Router Agent. 
Analyze this text: "I have a headache."
Respond ONLY with JSON containing 'intent' and 'symptoms'.
"""

try:
    # Notice we temporarily bumped max_tokens to 500 to test if it was starving!
    response = client.chat.completions.create(
        messages=[{"role": "user", "content": test_prompt}],
        max_tokens=500, 
        temperature=0.0
    )
    
    raw_text = response.choices[0].message.content
    
    print("\n===================================")
    print("🎯 RAW SERVER RESPONSE:")
    print(f"[{raw_text}]")
    print("===================================")
    
except Exception as e:
    print(f"\n❌ API ERROR: {e}")