import os

from dotenv import load_dotenv
from langchain_huggingface import HuggingFaceEndpointEmbeddings


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


def embed_documents(texts: list[str]) -> list[list[float]]:
    return embedding_model.embed_documents(texts)
