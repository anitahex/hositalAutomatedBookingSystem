import os

from dotenv import load_dotenv
from langchain_huggingface import HuggingFaceEndpointEmbeddings
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential
from huggingface_hub.errors import HfHubHTTPError


load_dotenv()

HF_TOKEN = os.getenv("HF_TOKEN")
EMBEDDING_MODEL_NAME = os.getenv(
    "HF_EMBEDDING_MODEL",
    "sentence-transformers/all-MiniLM-L6-v2",
)

if not HF_TOKEN:
    raise ValueError("HF_TOKEN must be set in your .env file.")


embedding_model = HuggingFaceEndpointEmbeddings(
    model=EMBEDDING_MODEL_NAME,
    task="feature-extraction",
    huggingfacehub_api_token=HF_TOKEN,
)


def embed_query(text: str) -> list[float]:
    return embedding_model.embed_query(text)


@retry(
    retry=retry_if_exception_type(HfHubHTTPError),
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=2, min=2, max=30),
    reraise=True,
)
def embed_documents(texts: list[str]) -> list[list[float]]:
    # The HF Inference API occasionally returns a transient 5xx (observed during
    # vector-store hydration, which fires hundreds of sequential batch calls) —
    # without a retry, one flaky call kills the entire hydration run.
    return embedding_model.embed_documents(texts)
