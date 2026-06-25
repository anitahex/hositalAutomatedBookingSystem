#!/bin/bash
set -e

echo "==> Waiting for Qdrant to be ready..."
python - <<'EOF'
import time, urllib.request, urllib.error
for _ in range(60):
    try:
        urllib.request.urlopen("http://qdrant:6333/healthz", timeout=3)
        print("Qdrant is ready.")
        break
    except Exception:
        time.sleep(2)
else:
    raise SystemExit("Qdrant did not become ready in time.")
EOF

INIT_FLAG="/app/data/.initialized"

if [ ! -f "$INIT_FLAG" ]; then
    echo "==> First boot: running database migrations..."
    alembic upgrade head

    echo "==> Loading doctors and appointment slots from CSV..."
    python -c "from app.db.ingest_relational import ingest_relational_data; ingest_relational_data()"

    echo "==> Hydrating Qdrant vector store (this may take a few minutes)..."
    python -c "from app.db.hydrate_vectors import hydrate_vector_db; hydrate_vector_db()"

    touch "$INIT_FLAG"
    echo "==> Initialisation complete."
fi

echo "==> Starting FastAPI server..."
exec python run.py
