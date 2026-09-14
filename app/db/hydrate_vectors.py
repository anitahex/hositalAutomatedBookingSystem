import pandas as pd

from app.services.embeddings import embed_documents
from app.services.vector_store import (
    QDRANT_COLLECTION,
    qdrant_client,
    recreate_clinical_collection,
    upsert_clinical_points,
)


BATCH_SIZE = 250


def _collection_already_hydrated(expected_count: int) -> bool:
    """Cheap, no-embedding-calls check against Qdrant's own state — used so
    ensure_vector_db_hydrated() can run on every boot without re-paying the real
    hydration cost (embedding-API calls across the whole CSV) when nothing changed.
    Any failure here (collection missing, Qdrant unreachable, etc.) is treated as
    'needs hydration' — if Qdrant is genuinely unreachable, the real hydration attempt
    right after this will fail loudly and clearly instead."""
    try:
        info = qdrant_client().get_collection(QDRANT_COLLECTION)
        return info.points_count == expected_count
    except Exception:
        return False


def ensure_vector_db_hydrated() -> None:
    """Safe to call on every boot (see docker-entrypoint.sh) — only pays the real
    hydration cost (embedding-API calls, collection recreate) once, then again only if
    Qdrant's state ever diverges from the CSV (e.g. a fresh/mismatched volume), rather
    than trusting a flag file decoupled from Qdrant's actual contents."""
    df = pd.read_csv("cleaned_hospital_rag_dataset.csv")
    if _collection_already_hydrated(len(df)):
        print(f"Qdrant vector hydration: {len(df)} records already present, skipping.")
        return
    hydrate_vector_db(df)


def hydrate_vector_db(df: pd.DataFrame | None = None):
    if df is None:
        df = pd.read_csv("cleaned_hospital_rag_dataset.csv")
    recreate_clinical_collection()

    for start in range(0, len(df), BATCH_SIZE):
        batch = df.iloc[start : start + BATCH_SIZE]
        chunks = batch["rag_optimized_chunk"].tolist()
        embeddings = embed_documents(chunks)

        records = [
            {
                "row_number": int(start + index),
                "department": row.department,
                "disease_name": row.disease_name,
                "chunk_text": row.rag_optimized_chunk,
                "embedding": embeddings[index],
            }
            for index, row in enumerate(batch.itertuples())
        ]

        upsert_clinical_points(records)
        print(f"Inserted vector records {start + 1}-{start + len(batch)}")

    print(f"Qdrant vector hydration complete: {len(df)} records.")
