import os

from dotenv import load_dotenv


load_dotenv()

HF_VISION_MODEL = os.getenv("HF_VISION_MODEL", "meta-llama/Llama-3.2-11B-Vision-Instruct")
