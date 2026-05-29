import os

from dotenv import load_dotenv
from huggingface_hub import InferenceClient


load_dotenv()

HF_TOKEN = os.getenv("HF_TOKEN")
HF_MODEL = os.getenv("HF_MODEL", "Qwen/Qwen3.6-35B-A3B")

if not HF_TOKEN:
    raise ValueError("HF_TOKEN must be set in your .env file.")

client = InferenceClient(model=HF_MODEL, token=HF_TOKEN, timeout=30)
response = client.chat.completions.create(
    messages=[{"role": "user", "content": "Reply with: model ok"}],
    max_tokens=20,
    temperature=0,
)

print(response.choices[0].message.content)
