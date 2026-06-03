from app.db.connection import connect_db


def ensure_chat_history_schema(conn):
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE EXTENSION IF NOT EXISTS pgcrypto;

            CREATE TABLE IF NOT EXISTS chat_messages (
                message_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                patient_id TEXT NOT NULL,
                role TEXT NOT NULL CHECK (role IN ('patient', 'assistant')),
                text TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT NOW()
            );

            CREATE INDEX IF NOT EXISTS idx_chat_messages_patient_created
                ON chat_messages(patient_id, created_at);
            """
        )


def load_recent_chat_history(patient_id: str, limit: int = 30):
    with connect_db() as conn:
        ensure_chat_history_schema(conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT role, text
                FROM (
                    SELECT role, text, created_at
                    FROM chat_messages
                    WHERE patient_id = %s
                    ORDER BY created_at DESC
                    LIMIT %s
                ) recent
                ORDER BY created_at ASC;
                """,
                (patient_id, limit),
            )
            rows = cur.fetchall()

    return [{"role": role, "text": text} for role, text in rows]


def append_chat_messages(patient_id: str, messages: list[dict]):
    clean_messages = [
        (patient_id, message.get("role"), message.get("text"))
        for message in messages
        if message.get("role") in {"patient", "assistant"} and message.get("text")
    ]
    if not clean_messages:
        return

    with connect_db() as conn:
        ensure_chat_history_schema(conn)
        with conn.cursor() as cur:
            cur.executemany(
                """
                INSERT INTO chat_messages (patient_id, role, text)
                VALUES (%s, %s, %s);
                """,
                clean_messages,
            )
        conn.commit()
