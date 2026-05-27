import pandas as pd

from app.services.embeddings import embed_documents
from app.services.vector_store import recreate_clinical_collection, upsert_clinical_points


BATCH_SIZE = 250


def hydrate_vector_db():
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
