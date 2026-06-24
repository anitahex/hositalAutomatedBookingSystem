import os

from dotenv import load_dotenv


load_dotenv()

HF_VISION_MODEL = os.getenv("HF_VISION_MODEL", "Qwen/Qwen2.5-VL-7B-Instruct")
