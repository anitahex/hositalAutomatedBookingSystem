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

    def box(x: int, y: int, w: int, h: int, label: str) -> list[str]:
        return [
            "0.8 w",
            f"{x} {y} {w} {h} re S",
            draw_text(x + 10, y + 15, label, font="F1", size=10),
        ]

    parts.extend(box(72, 690, 110, 42, "Frontend"))
    parts.extend(box(212, 690, 125, 42, "POST /chat"))
    parts.extend(box(367, 690, 122, 42, "run_patient_chat"))
    parts.extend(box(519, 690, 110, 42, "Supervisor"))
    parts.extend([
        "0.8 w",
        "182 711 m 212 711 l S",
        "337 711 m 367 711 l S",
        "489 711 m 519 711 l S",
    ])

    text, _ = draw_multiline(
        72,
        620,
        "The supervisor first checks deterministic shortcuts such as profile questions, booking lookup, cancellation, end-chat, and direct booking. If none match, it falls back to the LLM router.",
        size=10,
        width=88,
        line_gap=13,
    )
    parts.append(text)
    text, _ = draw_multiline(
        72,
        590,
        "After routing, the selected node updates GraphState and returns control to the supervisor until a final_response is produced or the graph reaches finish.",
        size=10,
        width=88,
        line_gap=13,
    )
    parts.append(text)
    parts.append(draw_text(72, 545, "Special Routes", font="F2", size=14))

    specials = [
        "Profile query -> finish with a direct response from patient_profile",
        "Symptoms -> triage_router -> conversation_agent -> remedy_agent",
        "Persisting symptoms -> medical_rag -> appointment_booker",
        "Doctor/department request -> appointment_booker, or medical_rag first when the department is unknown",
        "Booking lookup / cancellation / reschedule -> appointment_booker",
        "End chat -> end_confirmation -> finish",
    ]
    y = 520
    for item in specials:
        block, y = draw_multiline(84, y, "- " + item, size=11, width=84, line_gap=14)
        parts.append(block)
        y -= 4
    return "\n".join(parts)


def build_page_three() -> str:
    parts: list[str] = []
    parts.append(draw_text(72, 780, "Agents and Responsibilities", font="F2", size=16))
    y = 750
    items = [
        "Supervisor: decides whether the message continues the current flow or diverts to a specialist.",
        "Triage router: extracts intent, symptoms, and severity from the latest message.",
        "Conversation agent: asks follow-up intake questions until enough context is collected.",
        "Remedy agent: generates personalized care tips and handles follow-up about improvement or persistence.",
        "Medical RAG: maps symptoms and context to the most relevant department using heuristics, vector search, and LLM reasoning.",
        "Appointment booker: handles doctor selection, slot selection, booking confirmation, rescheduling, and cancellation.",
    ]
    for item in items:
        block, y = draw_multiline(72, y, "- " + item, size=11, width=85, line_gap=14)
        parts.append(block)
        y -= 2
    parts.append(draw_text(72, 610, "State That Drives Routing", font="F2", size=14))
    state_line, _ = draw_multiline(
        72,
        585,
        "awaiting, intent, symptoms, severity, target_department, remedy_given, persisting, booking_active, confirmed_booking, confirmed_bookings, chat_closed, and patient_profile.",
        size=11,
        width=85,
        line_gap=15,
    )
    parts.append(state_line)
    return "\n".join(parts)


def build_page_four() -> str:
    parts: list[str] = []
    parts.append(draw_text(72, 780, "Important Bypass Scenarios", font="F2", size=16))
    y = 750
    bypasses = [
        "Chat already closed: run_patient_chat returns a closed-chat response immediately.",
        "User asks for profile info: the supervisor answers from patient_profile and skips the medical flow.",
        "User asks for a booking lookup: the supervisor returns the active or past bookings summary.",
        "User asks for a remedy during booking: the booking state is cleared and the flow returns to remedy_agent.",
        "RAG cannot confidently match a department: the flow returns to conversation_agent for more intake.",
        "Emergency severity: the remedy step is bypassed in favor of emergency guidance.",
    ]
    for item in bypasses:
        block, y = draw_multiline(72, y, "- " + item, size=11, width=85, line_gap=14)
        parts.append(block)
        y -= 2
    parts.append(draw_text(72, 585, "Data Stores and Supporting Services", font="F2", size=14))
    services = [
        "Chat history and session summaries are persisted by app/services/chat_history.py and app/services/llm_usage.py.",
        "Appointments use app/services/appointments.py and the routes in app/api/routes/appointments.py.",
        "Medical department matching uses app/services/rag.py with vector search and reranking.",
        "Database schema and rebuild scripts live under app/db.",
    ]
    y = 560
    for item in services:
        block, y = draw_multiline(72, y, "- " + item, size=11, width=85, line_gap=14)
        parts.append(block)
        y -= 2
    return "\n".join(parts)


def main() -> None:
    builder = PdfBuilder()
    builder.add_page(build_page_one())
    builder.add_page(build_page_two())
    builder.add_page(build_page_three())
    builder.add_page(build_page_four())
    OUTPUT.write_bytes(builder.build())
    print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main()
