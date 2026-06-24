import os

from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.http.exceptions import ResponseHandlingException, UnexpectedResponse


load_dotenv()

QDRANT_MODE = os.getenv("QDRANT_MODE", "remote").lower()
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY") or None
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "clinical_knowledge_base")
QDRANT_LOCAL_PATH = os.getenv("QDRANT_LOCAL_PATH", "qdrant_storage")
VECTOR_SIZE = int(os.getenv("VECTOR_SIZE", "384"))


def validate_qdrant_config():
    if QDRANT_MODE == "local":
        return

    if not QDRANT_URL:
        raise ValueError("QDRANT_URL must be set in your .env file.")

    if "your-cluster-url" in QDRANT_URL:
        raise ValueError(
            "QDRANT_URL is still the placeholder value. Replace it with your real "
            "Qdrant Cloud cluster URL, for example "
            "https://xxxxxx.region.cloud.qdrant.io."
        )


def qdrant_client():
    validate_qdrant_config()

    if QDRANT_MODE == "local":
        return QdrantClient(
            path=QDRANT_LOCAL_PATH,
            timeout=120,
            force_disable_check_same_thread=True,
        )

    return QdrantClient(
        url=QDRANT_URL,
        api_key=QDRANT_API_KEY,
        timeout=120,
    )


def run_qdrant_operation(operation):
    try:
        return operation()
    except (ResponseHandlingException, UnexpectedResponse) as exc:
        raise RuntimeError(
            "Could not connect to Qdrant. For local embedded mode, set "
            "QDRANT_MODE=local. For remote mode, check QDRANT_URL and "
            "QDRANT_API_KEY in .env, and make sure the Qdrant cluster is reachable."
        ) from exc


def search_clinical_knowledge(query_vector: list[float], limit: int = 1):
    result = run_qdrant_operation(
        lambda: qdrant_client().query_points(
            collection_name=QDRANT_COLLECTION,
            query=query_vector,
            limit=limit,
            with_payload=True,
        )
    )
    return result.points
