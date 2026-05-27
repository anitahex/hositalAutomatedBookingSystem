import os

from dotenv import load_dotenv


load_dotenv()

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY")
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "hospital-raw-files")


def object_store_configured() -> bool:
    return bool(MINIO_ACCESS_KEY and MINIO_SECRET_KEY)
