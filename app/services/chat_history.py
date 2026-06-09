from app.db.connection import connect_db


def ensure_chat_history_schema(conn):
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE EXTENSION IF NOT EXISTS pgcrypto;

            CREATE TABLE IF NOT EXISTS chat_messages (
                message_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                patient_id TEXT NOT NULL,
                chat_session_id UUID,
                role TEXT NOT NULL CHECK (role IN ('patient', 'assistant')),
                text TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT NOW()
            );

            ALTER TABLE chat_messages
                ADD COLUMN IF NOT EXISTS chat_session_id UUID;

            CREATE INDEX IF NOT EXISTS idx_chat_messages_patient_created
                ON chat_messages(patient_id, created_at);
            CREATE INDEX IF NOT EXISTS idx_chat_messages_patient_session_created
                ON chat_messages(patient_id, chat_session_id, created_at);
            """
        )


def load_recent_chat_history(patient_id: str, limit: int = 30, chat_session_id: str | None = None):
    with connect_db() as conn:
        ensure_chat_history_schema(conn)
        with conn.cursor() as cur:
            if chat_session_id:
                cur.execute(
                    """
                    SELECT role, text
                    FROM (
                        SELECT role, text, created_at
                        FROM chat_messages
                        WHERE patient_id = %s
                            AND chat_session_id = %s
                        ORDER BY created_at DESC
                        LIMIT %s
                    ) recent
                    ORDER BY created_at ASC;
                    """,
                    (patient_id, chat_session_id, limit),
                )
            else:
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


def load_chat_sessions_with_messages(patient_id: str, limit: int = 100):
    with connect_db() as conn:
        ensure_chat_history_schema(conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT chat_session_id::text, role, text, created_at
                FROM chat_messages
                WHERE patient_id = %s
                ORDER BY created_at DESC
                LIMIT %s;
                """,
                (patient_id, limit),
            )
            rows = cur.fetchall()

    messages = []
    for chat_session_id, role, text, created_at in reversed(rows):
        created_at_iso = created_at.isoformat()
        session_id = chat_session_id or f"legacy-{created_at_iso[:10]}"
        messages.append(
            {
                "chat_session_id": session_id,
                "role": role,
                "text": text,
                "created_at": created_at_iso,
            }
        )

    sessions = []
    by_session = {}
    for message in messages:
        session_id = message["chat_session_id"]
        if session_id not in by_session:
            session = {
                "chat_session_id": session_id,
                "date": message["created_at"][:10],
                "started_at": message["created_at"],
                "updated_at": message["created_at"],
                "title": "New conversation",
                "message_count": 0,
                "messages": [],
            }
            by_session[session_id] = session
            sessions.append(session)
        by_session[session_id]["messages"].append(message)
        by_session[session_id]["updated_at"] = message["created_at"]
        by_session[session_id]["message_count"] += 1

        if by_session[session_id]["title"] == "New conversation" and message["role"] == "patient":
            title = " ".join(message["text"].split())
            by_session[session_id]["title"] = title[:64] + ("..." if len(title) > 64 else "")

    return list(reversed(sessions))


def load_chat_history_with_timestamps(patient_id: str, limit: int = 100):
    sessions = load_chat_sessions_with_messages(patient_id, limit)
    return [
        message
        for session in sessions
        for message in session["messages"]
    ]


def append_chat_messages(patient_id: str, messages: list[dict], chat_session_id: str | None = None):
    clean_messages = [
        (patient_id, chat_session_id, message.get("role"), message.get("text"))
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
                INSERT INTO chat_messages (patient_id, chat_session_id, role, text)
                VALUES (%s, %s, %s, %s);
                """,
                clean_messages,
            )
        conn.commit()
