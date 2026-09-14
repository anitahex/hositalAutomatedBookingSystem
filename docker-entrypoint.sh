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

# Every step below is self-checking and safe to run on EVERY boot, not gated behind a
# one-time flag file. The previous design used a marker file in the app_data volume to
# run these only "on first boot" — but that flag is decoupled from whether postgres_data
# (a separate volume) actually has any rows in it. If the two volumes ever end up out of
# sync (a recreated Postgres volume, a different DATABASE_URL, a partial earlier deploy),
# the flag stays present forever while doctors/appointment_slots silently stay empty,
# with no error anywhere — every availability query just returns zero results. See
# TECH_DEBT.md for the full incident writeup.
echo "==> Running database migrations..."
alembic upgrade head

echo "==> Loading doctors and appointment slots from CSV..."
python -c "from app.db.ingest_relational import ingest_relational_data; ingest_relational_data()"

echo "==> Ensuring Qdrant vector store is hydrated..."
python -c "from app.db.hydrate_vectors import ensure_vector_db_hydrated; ensure_vector_db_hydrated()"

echo "==> Starting FastAPI server..."
exec python run.py
