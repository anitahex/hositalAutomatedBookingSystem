from __future__ import annotations

from pathlib import Path
import textwrap


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs" / "project_architecture_agent_flow.pdf"


class PdfBuilder:
    def __init__(self, page_width: int = 595, page_height: int = 842):
        self.page_width = page_width
        self.page_height = page_height
        self.pages: list[str] = []

    def add_page(self, content_stream: str) -> None:
        self.pages.append(content_stream)

    def build(self) -> bytes:
        objects: list[bytes | None] = [None]
        objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")  # 1
        objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>")  # 2

        page_count = len(self.pages)
        page_obj_ids = [5 + (i * 2) for i in range(page_count)]
        kids = " ".join(f"{page_id} 0 R" for page_id in page_obj_ids)
        objects.append(f"<< /Type /Pages /Kids [{kids}] /Count {page_count} >>".encode("latin-1"))  # 3

        for index, content_stream in enumerate(self.pages):
            content_obj_id = 4 + (index * 2)
            page_obj_id = 5 + (index * 2)
            stream_bytes = content_stream.encode("latin-1")
            objects.append(
                b"<< /Length %d >>\nstream\n" % len(stream_bytes) + stream_bytes + b"\nendstream"
            )
            objects.append(
                (
                    f"<< /Type /Page /Parent 3 0 R /MediaBox [0 0 {self.page_width} {self.page_height}] "
                    f"/Resources << /Font << /F1 1 0 R /F2 2 0 R >> >> /Contents {content_obj_id} 0 R >>"
                ).encode("latin-1")
            )
            assert page_obj_id == len(objects) - 1

        catalog_obj_id = len(objects)
        objects.append(b"<< /Type /Catalog /Pages 3 0 R >>")

        out = bytearray(b"%PDF-1.4\n")
        offsets = [0]
        for idx, obj in enumerate(objects[1:], start=1):
            if obj is None:
                raise RuntimeError(f"Missing PDF object {idx}")
            offsets.append(len(out))
            out.extend(f"{idx} 0 obj\n".encode("latin-1"))
            out.extend(obj)
            out.extend(b"\nendobj\n")

        xref_pos = len(out)
        out.extend(f"xref\n0 {len(objects)}\n".encode("latin-1"))
        out.extend(b"0000000000 65535 f \n")
        for offset in offsets[1:]:
            out.extend(f"{offset:010d} 00000 n \n".encode("latin-1"))
        out.extend(
            f"trailer\n<< /Size {len(objects)} /Root {catalog_obj_id} 0 R >>\nstartxref\n{xref_pos}\n%%EOF\n".encode("latin-1")
        )
        return bytes(out)


def esc(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def wrap_text(text: str, width: int) -> list[str]:
    paragraphs = text.splitlines() or [""]
    lines: list[str] = []
    for paragraph in paragraphs:
        if not paragraph.strip():
            lines.append("")
            continue
        wrapped = textwrap.wrap(
            paragraph,
            width=width,
            break_long_words=False,
            break_on_hyphens=False,
        )
        lines.extend(wrapped or [""])
    return lines


def draw_text(x: int, y: int, text: str, font: str = "F1", size: int = 11) -> str:
    return "\n".join([
        "BT",
        f"/{font} {size} Tf",
        f"1 0 0 1 {x} {y} Tm",
        f"({esc(text)}) Tj",
        "ET",
    ])


def draw_multiline(x: int, y: int, text: str, font: str = "F1", size: int = 11, width: int = 82, line_gap: int = 15) -> tuple[str, int]:
    lines = wrap_text(text, width=width)
    parts: list[str] = []
    current_y = y
    for line in lines:
        if not line:
            current_y -= line_gap
            continue
        parts.append(draw_text(x, current_y, line, font=font, size=size))
        current_y -= line_gap
    return "\n".join(parts), current_y


def build_page_one() -> str:
    parts: list[str] = []
    parts.append(draw_text(72, 785, "Hospital Automated Booking System", font="F2", size=22))
    parts.append(draw_text(72, 760, "Project Architecture and Agent Flow", font="F2", size=14))
    body, _ = draw_multiline(
        72,
        735,
        "This PDF summarizes the current backend architecture, the LangGraph routing loop, and the main patient flows in the Smart Hospital Portal.",
        size=11,
        width=82,
        line_gap=15,
    )
    parts.append(body)
    parts.append(draw_text(72, 675, "Core Architecture", font="F2", size=14))
    y = 650
    bullets = [
        "Frontend: app/api/static/index.html, app.js, and styles.css render the portal UI and send chat requests.",
        "API layer: app/api/main.py exposes auth, chat, appointments, and admin routers.",
        "Chat route: app/api/routes/chat.py loads the patient profile, history, active appointments, and executes the agent graph.",
        "Agent graph: app/agents/graph.py runs the LangGraph workflow and keeps the conversation memory compacted.",
        "Supervisor router: app/agents/supervisor.py decides the next specialist or ends the turn.",
        "Specialist agents: triage_router, conversation_agent, remedy_agent, medical_rag, and appointment_booker handle the medical and booking steps.",
        "Services: app/services and app/db provide chat history, appointment operations, memory policy, embeddings, vector search, token tracking, and persistence.",
    ]
    for bullet in bullets:
        block, y = draw_multiline(72, y, "- " + bullet, size=11, width=82, line_gap=15)
        parts.append(block)
        y -= 3
    return "\n".join(parts)


def build_page_two() -> str:
    parts: list[str] = []
    parts.append(draw_text(72, 780, "Primary Runtime Flow", font="F2", size=16))
    text, _ = draw_multiline(
        72,
        742,
        "Frontend -> POST /chat or /chat/stream -> run_patient_chat -> LangGraph supervisor -> specialist agent -> supervisor -> final response.",
        size=11,
        width=84,
        line_gap=15,
    )
    parts.append(text)
    parts.append(draw_text(72, 690, "What The Supervisor Checks First", font="F2", size=14))
    checks = [
        "Profile and account questions",
        "Chat end / close requests",
        "Booking lookup, cancel, or reschedule requests",
        "Direct booking requests",
        "Symptom triage or medical routing",
    ]
    y = 665
    for item in checks:
        parts.append(draw_text(84, y, f"- {item}", size=11))
        y -= 24
    parts.append(draw_text(72, 530, "Special Routes", font="F2", size=14))
    specials = [
        "Profile query -> answer from patient_profile and bypass medical agents.",
        "Symptoms -> triage_router -> conversation_agent -> remedy_agent.",
        "Persisting symptoms -> medical_rag -> appointment_booker.",
        "Unknown department -> medical_rag before booking.",
        "Booking lookup, cancellation, reschedule -> appointment_booker.",
        "End chat -> end_confirmation -> finish.",
    ]
    y = 505
    for item in specials:
        block, y = draw_multiline(84, y, "- " + item, size=11, width=84, line_gap=15)
        parts.append(block)
        y -= 4
    return "\n".join(parts)


def build_page_three() -> str:
    parts: list[str] = []
    parts.append(draw_text(72, 780, "Agents and Responsibilities", font="F2", size=16))
    y = 748
    items = [
        "Supervisor: decides whether the message continues the current flow or diverts to a specialist.",
        "Triage router: extracts intent, symptoms, and severity from the latest message.",
        "Conversation agent: asks follow-up intake questions until enough context is collected.",
        "Remedy agent: generates personalized care tips and handles follow-up about improvement or persistence.",
        "Medical RAG: maps symptoms and context to the most relevant department using heuristics, vector search, and LLM reasoning.",
        "Appointment booker: handles doctor selection, slot selection, booking confirmation, rescheduling, and cancellation.",
    ]
    for item in items:
        block, y = draw_multiline(72, y, "- " + item, size=11, width=78, line_gap=17)
        parts.append(block)
        y -= 8
    parts.append(draw_text(72, 540, "State That Drives Routing", font="F2", size=14))
    state_line, _ = draw_multiline(
        72,
        515,
        "awaiting, intent, symptoms, severity, target_department, remedy_given, persisting, booking_active, confirmed_booking, confirmed_bookings, chat_closed, and patient_profile.",
        size=11,
        width=76,
        line_gap=16,
    )
    parts.append(state_line)
    return "\n".join(parts)


def build_page_four() -> str:
    parts: list[str] = []
    parts.append(draw_text(72, 780, "Important Bypass Scenarios", font="F2", size=16))
    y = 748
    bypasses = [
        "Chat already closed: run_patient_chat returns a closed-chat response immediately.",
        "User asks for profile info: the supervisor answers from patient_profile and skips the medical flow.",
        "User asks for a booking lookup: the supervisor returns the active or past bookings summary.",
        "User asks for a remedy during booking: the booking state is cleared and the flow returns to remedy_agent.",
        "RAG cannot confidently match a department: the flow returns to conversation_agent for more intake.",
        "Emergency severity: the remedy step is bypassed in favor of emergency guidance.",
    ]
    for item in bypasses:
        block, y = draw_multiline(72, y, "- " + item, size=11, width=78, line_gap=17)
        parts.append(block)
        y -= 8
    parts.append(draw_text(72, 540, "Data Stores and Supporting Services", font="F2", size=14))
    services = [
        "Chat history and session summaries are persisted by app/services/chat_history.py and app/services/llm_usage.py.",
        "Appointments use app/services/appointments.py and the routes in app/api/routes/appointments.py.",
        "Medical department matching uses app/services/rag.py with vector search and reranking.",
        "Database schema and rebuild scripts live under app/db.",
    ]
    y = 515
    for item in services:
        block, y = draw_multiline(72, y, "- " + item, size=11, width=78, line_gap=17)
        parts.append(block)
        y -= 8
    return "\n".join(parts)


def build_page_five() -> str:
    parts: list[str] = []
    parts.append(draw_text(72, 780, "API Surface and Functions Used", font="F2", size=16))
    y = 748
    api_items = [
        "Auth API: POST /auth/signup, POST /auth/login, POST /auth/admin/login, GET /auth/me, PATCH /auth/profile.",
        "Chat API: POST /chat, POST /chat/stream, GET /chat/history, POST /chat/upload, POST /chat/confirm-processing, GET /chat/document-status/{id}.",
        "Appointment API: GET /appointments/departments, /doctors, /slots, /available, /upcoming, /previous, POST /book, /{id}/cancel, /{id}/reschedule, GET /{id}/reschedule-options.",
        "Admin API: analytics, doctors, slots, holidays, and appointment dashboard endpoints under /admin.",
        "WebSockets: /ws/status/{session_id} for document-ingestion progress and /chat/deepgram for live audio bridging.",
    ]
    for item in api_items:
        block, y = draw_multiline(72, y, "- " + item, size=11, width=78, line_gap=17)
        parts.append(block)
        y -= 8
    parts.append(draw_text(72, 540, "Main Functions", font="F2", size=14))
    y = 515
    functions = [
        "app/api/main.py: FastAPI app creation, lifespan startup, health check, static file serving, and WebSocket connection manager.",
        "app/api/routes/chat.py: _prepare_chat_state, _run_chat_with_usage, chat, chat_stream, upload_document, confirm_processing, document_status.",
        "app/agents/graph.py: initialise_hybrid_memory, compact_hybrid_memory, arun_patient_chat, run_patient_chat.",
        "app/agents/supervisor.py: supervisor_node, route_from_supervisor, continue_current_node, general_qa_node, routing heuristics.",
        "app/agents/triage_router.py: triage_router_node and triage streaming helpers.",
        "app/agents/conversation_agent.py: conversation_agent_node, conversation_agent_stream, finalize_conv_stream_state.",
        "app/agents/remedy_agent.py: remedy_agent_node.",
        "app/agents/medical_rag.py: medical_rag_node.",
        "app/agents/appointment_booker.py: appointment_booker_node and booking-menu helpers.",
        "app/agents/document_analyzer.py: document_analyzer_node.",
    ]
    for item in functions:
        block, y = draw_multiline(72, y, "- " + item, size=10, width=78, line_gap=15)
        parts.append(block)
        y -= 8
    return "\n".join(parts)


def build_page_six() -> str:
    parts: list[str] = []
    parts.append(draw_text(72, 780, "How The App Handles 100000 Users", font="F2", size=16))
    y = 748
    items = [
        "Short answer: not safely as-is. The code is structured well, but it is not yet production-hardened for 100000 truly simultaneous users.",
        "Current bottlenecks: psycopg2.connect() creates a fresh blocking DB connection per call; the app does not show an async database pool; LLM calls and vector searches can become latency hotspots; document extraction is CPU-heavy; and LangGraph checkpoints are stored in SQLite, which is not ideal for massive concurrent writes.",
        "What already helps: conversation memory is compacted, recent-history windows are small, static prompts are reused, booking lookups are limited, and session state is namespaced by patient_id + session_id to reduce leakage.",
        "What would be needed for 100k scale: a real PostgreSQL connection pool, async DB access or worker isolation, Redis or another external session/cache layer, separate queues for document ingestion and long LLM jobs, horizontal stateless API replicas behind a load balancer, and rate limits with backpressure.",
        "Critical booking safety: slot booking must stay transactional with unique constraints and row locks so two users cannot reserve the same slot at once.",
        "Operational reality: 100000 simultaneous browser sessions is different from 100000 active LLM calls. The app can support many idle sessions only if chat state is kept out of process and expensive work is throttled.",
    ]
    for item in items:
        block, y = draw_multiline(72, y, "- " + item, size=11, width=78, line_gap=17)
        parts.append(block)
        y -= 8
    parts.append(draw_text(72, 540, "Recommended Hardening Plan", font="F2", size=14))
    y = 515
    plan = [
        "1. Replace psycopg2 connect-per-call usage with a pooled async layer or a shared PgBouncer-backed pool.",
        "2. Move SQLite checkpoints to PostgreSQL or Redis for multi-replica durability.",
        "3. Put document analysis and any long-running LLM work on background workers.",
        "4. Add Redis-backed rate limiting, per-user quotas, and request timeouts.",
        "5. Cache department lookups, doctor lists, and common prompts where safe.",
        "6. Load test booking writes separately from read-heavy chat traffic.",
    ]
    for item in plan:
        block, y = draw_multiline(72, y, item, size=10, width=78, line_gap=15)
        parts.append(block)
        y -= 8
    return "\n".join(parts)


def build_page_seven() -> str:
    parts: list[str] = []
    parts.append(draw_text(72, 780, "Data Stores, Integrations, and Runtime Notes", font="F2", size=16))
    y = 748
    items = [
        "PostgreSQL stores users, patient profiles, doctors, slots, holidays, bookings, chat history, admin data, token logs, and document catalog rows.",
        "Qdrant stores the clinical knowledge base that powers department matching and medical RAG.",
        "Azure OpenAI is used for chat generation, routing, summary generation, document relevance checks, and document extraction.",
        "Azure Blob Storage stores staged uploads, vault files, and generated JSON summaries.",
        "Sentence Transformers provide embeddings for vector search, and optional CrossEncoder reranking improves department matching.",
        "Nginx serves the frontend and reverse-proxies API and WebSocket traffic.",
    ]
    for item in items:
        block, y = draw_multiline(72, y, "- " + item, size=11, width=78, line_gap=17)
        parts.append(block)
        y -= 8
    parts.append(draw_text(72, 540, "Key Runtime Safeguards", font="F2", size=14))
    y = 515
    guards = [
        "JWT authentication is required for patient actions.",
        "Profile data and bookings are reloaded from the database each turn instead of trusting client state.",
        "Chat state uses patient_id plus session_id thread IDs to reduce cross-user leakage.",
        "Document uploads are size-limited, MIME-filtered, and verified before staging.",
        "Booking queries respect a 30-minute minimum lead time and a 7-day lookahead window.",
    ]
    for item in guards:
        block, y = draw_multiline(72, y, "- " + item, size=11, width=78, line_gap=17)
        parts.append(block)
        y -= 8
    return "\n".join(parts)


def main() -> None:
    builder = PdfBuilder()
    builder.add_page(build_page_one())
    builder.add_page(build_page_two())
    builder.add_page(build_page_three())
    builder.add_page(build_page_four())
    builder.add_page(build_page_five())
    builder.add_page(build_page_six())
    builder.add_page(build_page_seven())
    OUTPUT.write_bytes(builder.build())
    print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main()
