import requests
import os
from dotenv import load_dotenv

load_dotenv()

r = requests.get(
    "https://openrouter.ai/api/v1/models",
    headers={"Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}"}
)

free = [
    m["id"] for m in r.json()["data"]
    if str(m.get("pricing", {}).get("completion", "1")) == "0"
]

print("\n".join(sorted(free)))
