# Hospital Assistant — Automated Booking System

An AI-powered hospital assistant that handles clinical intake, symptom triage, department routing, appointment booking, and pre-appointment clinical documentation — all through a natural-language chat interface.

---

## Features

- **Conversational Clinical Intake** — Dynamic, probing questions tailored to patient responses (up to 6 turns), tracking symptoms, severity, duration, location, and triggers without repeating topics
- **Symptom Triage & Department Routing** — Hybrid vector search (Qdrant) + rule-based scoring maps symptoms to the correct department (Cardiology, Neurology, Orthopedics, ENT, etc.) with cross-encoder reranking
- **Doctor & Slot Selection** — Filters doctors by department and date; shows available slots in IST within a 7-day window, always 30+ minutes ahead of current time
- **Appointment Management** — Book, cancel (>24 h policy), and reschedule appointments through chat or the sidebar panel
- **Home Care Remedies** — Evidence-based temporary care advice specific to the patient's symptoms, with a feedback loop to escalate to booking if symptoms persist
- **Pre-Appointment Clinical Summary** — GPT-generated structured clinical notes forwarded to the doctor before the appointment, with patient consent
- **Medical Document Ingestion** — Upload PDFs and images via chat; Azure GPT-4o extracts structured data and stores it in a persistent document vault
- **Real-time Streaming** — WebSocket-based response streaming with live typing indicator
- **Chat History** — Full conversation history per case, browsable in the sidebar

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.11 · FastAPI · Uvicorn |
| AI Orchestration | LangGraph · LangChain |
| LLM | Azure OpenAI (GPT-4.1 Mini for chat/routing · GPT-4o for vision/extraction) |
| Embeddings | Sentence Transformers (384-dim) via Hugging Face |
| Vector Store | Qdrant |
| Relational DB | PostgreSQL 15 |
| State Checkpoints | SQLite (LangGraph checkpointer) |
| File Storage | Azure Blob Storage |
| Frontend | Vanilla JS · HTML5 · CSS3 |
| Reverse Proxy | Nginx |
| Containerization | Docker · Docker Compose |

---

## Architecture

```
User Browser
    │
    ▼
Nginx (port 8010)
 ├── /static/          → Serve SPA (index.html + app.js + styles.css)
 ├── /ws/              → WebSocket proxy → FastAPI backend
 └── /auth /chat /appointments /admin → FastAPI backend
         │
         ▼
    FastAPI (port 8010)
         │
         ▼
  LangGraph Workflow
  ┌──────────────────────────────────────────────┐
  │  Supervisor  ──routes──► Triage Router        │
  │      │                   Conversation Agent   │
  │      │                   Medical RAG          │
  │      │                   Remedy Agent         │
  │      │                   Checkup Report       │
  │      │                   Appointment Booker   │
  │      └───────────────────Document Analyzer    │
  └──────────────────────────────────────────────┘
         │
   ┌─────┼──────────┐
   ▼     ▼          ▼
PostgreSQL  Qdrant  Azure Blob
```

---

## Project Structure

```
hositalAutomatedBookingSystem/
├── app/
│   ├── agents/
│   │   ├── supervisor.py          # Master router — controls all state transitions
│   │   ├── triage_router.py       # Intent classification & severity assessment
│   │   ├── conversation_agent.py  # Dynamic clinical intake questioner
│   │   ├── remedy_agent.py        # Home care recommendations
│   │   ├── medical_rag.py         # Vector search → department matching
│   │   ├── checkup_report.py      # Pre-appointment clinical summary generator
│   │   ├── appointment_booker.py  # Doctor/slot selection, booking, reschedule
│   │   ├── document_analyzer.py   # PDF/image medical document analysis
│   │   ├── graph.py               # LangGraph workflow definition
│   │   ├── state.py               # GraphState TypedDict schema
│   │   ├── schemas.py             # Pydantic output models
│   │   └── intake_utils.py        # Shared intake utilities
│   ├── api/
│   │   ├── main.py                # FastAPI app, WebSocket manager, lifespan
│   │   ├── dependencies.py        # JWT authentication dependency
│   │   ├── routes/
│   │   │   ├── auth.py            # Signup, login, profile
│   │   │   ├── chat.py            # /chat/stream, /chat/upload, WebSocket
│   │   │   ├── appointments.py    # Booking CRUD, slots, reschedule
│   │   │   └── admin.py           # Admin utilities
│   │   └── static/
│   │       ├── index.html         # SPA entry point
│   │       ├── app.js             # Chat UI, WebSocket client, state rendering
│   │       ├── styles.css         # UI styling
│   │       └── med_logo.png       # Hospital logo
│   ├── services/
│   │   ├── appointments.py        # Slot queries, booking logic, IST conversion
│   │   ├── rag.py                 # Qdrant vector search & department scoring
│   │   ├── chat_history.py        # Persist/load conversation history
│   │   ├── checkpoint_store.py    # LangGraph SQLite checkpointer
│   │   ├── document_pipeline.py   # File upload validation & extraction
│   │   ├── document_catalog.py    # Postgres document metadata catalog
│   │   ├── blob_storage.py        # Azure Blob Storage integration
│   │   ├── vector_store.py        # Qdrant client wrapper
│   │   ├── embeddings.py          # Sentence Transformer wrapper
│   │   ├── users.py               # Patient auth & profile management
│   │   ├── tokens.py              # JWT generation
│   │   ├── memory_policy.py       # Per-agent context window settings
│   │   └── llm_usage.py           # Token tracking & cost analytics
│   ├── inference/
│   │   ├── llm.py                 # Azure OpenAI text generation (sync + async)
│   │   ├── azure_client.py        # GPT-4o client for vision/extraction
│   │   └── vision.py              # Vision model utilities
│   └── db/
│       ├── connection.py          # PostgreSQL connection pooling
│       ├── ingest_relational.py   # Load doctors_roster.csv & slots CSV
│       ├── hydrate_vectors.py     # Populate Qdrant from clinical dataset
│       └── rebuild_database.py    # Full DB initialization
├── alembic/
│   ├── versions/
│   │   └── 0001_initial_schema.py # Initial DB schema migration
│   └── env.py
├── docker-compose.yml
├── Dockerfile                     # Python 3.11 backend image
├── Dockerfile.frontend            # Nginx frontend image
├── docker-entrypoint.sh           # Migrations + data ingestion + server start
├── nginx.conf
├── requirements.txt
├── run.py                         # Local dev entry point
├── doctors_roster.csv             # Seed data: doctors & departments
├── appointment_slots.csv          # Seed data: available time slots
└── cleaned_hospital_rag_dataset.csv  # Clinical knowledge base for Qdrant
```

---

## Agents

| Agent | Responsibility |
|---|---|
| **Supervisor** | Master router — controls conversation flow, state transitions, and fallback routing using heuristics + LLM decisions |
| **Triage Router** | Classifies intent (greeting / triage / direct booking), extracts initial symptoms, and assesses severity (mild → emergency) |
| **Conversation Agent** | Asks up to 6 targeted follow-up questions (duration, location, triggers, patterns, associated symptoms, functional impact) without repeating topics |
| **Medical RAG** | Queries the Qdrant clinical knowledge base and applies hybrid scoring to route the patient to the correct department |
| **Remedy Agent** | Generates 2-3 evidence-based home care tips and asks whether symptoms improved before offering to book an appointment |
| **Checkup Report** | Generates a structured pre-appointment clinical summary using GPT and offers to forward it to the doctor |
| **Appointment Booker** | Manages the full booking workflow — doctor list, slot selection, confirmation, cancellation, and rescheduling |
| **Document Analyzer** | Processes uploaded PDFs and images using Azure GPT-4o, extracts structured clinical data, and maps findings to a department |

---

## API Endpoints

### Auth
| Method | Path | Description |
|---|---|---|
| POST | `/auth/signup` | Register new patient (email, password, name, age, blood group) |
| POST | `/auth/login` | Authenticate and receive JWT token |
| GET | `/auth/me` | Get current patient profile |
| PATCH | `/auth/profile` | Update health issues, contact, address |

### Chat
| Method | Path | Description |
|---|---|---|
| POST | `/chat/stream` | Send message; streams AI response via WebSocket |
| POST | `/chat/upload` | Upload medical document (PDF/image) |
| GET | `/chat/history` | Retrieve chat sessions for the current patient |
| WS | `/ws/{session_id}` | WebSocket connection for real-time streaming |

### Appointments
| Method | Path | Description |
|---|---|---|
| GET | `/appointments/departments` | List available departments |
| GET | `/appointments/doctors` | List doctors (filter by department, date) |
| GET | `/appointments/slots` | Available slots for a doctor on a date |
| POST | `/appointments/book` | Book a slot |
| GET | `/appointments/upcoming` | Patient's upcoming bookings |
| GET | `/appointments/previous` | Patient's past appointments |
| POST | `/appointments/{id}/cancel` | Cancel booking (>24 h policy) |
| GET | `/appointments/{id}/reschedule-options` | Available reschedule slots |
| POST | `/appointments/{id}/reschedule` | Reschedule to a new slot |

---

## Getting Started

### Prerequisites

- Docker and Docker Compose
- Azure OpenAI resource with `gpt-4.1-mini` and `gpt-4o` deployments
- Azure Blob Storage container (for document uploads)

### 1. Configure Environment

Create a `.env` file in the project root. The variables below are the only ones you need to supply — `DATABASE_URL`, `QDRANT_URL`, and `QDRANT_MODE` are already set by `docker-compose.yml` and do not need to be in `.env`.

```env
# Authentication
JWT_SECRET=your-long-random-secret-min-32-chars
JWT_EXP_SECONDS=604800

# Azure OpenAI — conversation, routing, summaries
AZURE_CONV_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_CONV_API_KEY=your-key
AZURE_CONV_DEPLOYMENT=gpt-4.1-mini
AZURE_ROUTER_DEPLOYMENT=gpt-4.1-mini
AZURE_SUMMARY_DEPLOYMENT=gpt-4.1-mini

# Azure OpenAI — vision / document extraction
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your-key
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4o

# Azure Blob Storage
AZURE_STORAGE_CONNECTION_STRING=DefaultEndpointsProtocol=https;AccountName=...
AZURE_CONTAINER_NAME=hospital-documents

# Qdrant collection settings
QDRANT_COLLECTION=clinical_knowledge_base
VECTOR_SIZE=384
```

### 2. Run with Docker Compose

```bash
docker compose up -d
```

This starts four services:

| Service | Image | Internal Port | Exposed |
|---|---|---|---|
| `postgres` | postgres:15-alpine | 5432 | No |
| `qdrant` | qdrant/qdrant:latest | 6333 | No |
| `backend` | ./Dockerfile | 8010 | No |
| `frontend` | ./Dockerfile.frontend | 80 | **8010** |

**Persistent volumes** (survive container restarts):

| Volume | Contents |
|---|---|
| `postgres_data` | PostgreSQL data directory |
| `qdrant_data` | Qdrant vector index storage |
| `app_data` | LangGraph SQLite checkpoints (`/app/data/`) |

On first start, the entrypoint automatically:
1. Waits for PostgreSQL to pass its health check and Qdrant to start
2. Runs Alembic migrations (`alembic upgrade head`)
3. Seeds the doctor roster and appointment slots from the CSV files
4. Populates the Qdrant clinical knowledge base from the clinical dataset

The app is available at **http://localhost:8010**

### 3. Local Development (without Docker)

```bash
pip install -r requirements.txt
# Export the variables from .env into your shell, then:
python run.py
```

> **Note for Windows:** `run.py` sets `WindowsSelectorEventLoopPolicy` automatically to fix the asyncio + aiohttp compatibility issue.

---

## Database Migrations

Migrations are managed with Alembic.

```bash
# Apply all pending migrations
alembic upgrade head

# Create a new migration
alembic revision --autogenerate -m "description"

# Rollback one step
alembic downgrade -1
```

---

## Data Files

| File | Purpose |
|---|---|
| `doctors_roster.csv` | Doctor names, departments, and years of experience — seeded into PostgreSQL on startup |
| `appointment_slots.csv` | Available appointment slots with doctor IDs and timestamps — seeded into PostgreSQL on startup |
| `cleaned_hospital_rag_dataset.csv` | Clinical knowledge base (symptoms → department mappings) — ingested into Qdrant on startup |

---

## Deployment Notes

- **Timezone**: The backend stores all timestamps in UTC. Slot times are converted to IST (UTC+5:30) before being sent to the frontend.
- **Slot policy**: Only slots more than 30 minutes ahead of the current time are shown; bookings are available for the next 7 days.
- **Cancellation policy**: Appointments can only be cancelled or rescheduled more than 24 hours before the scheduled time.
- **Document security**: Uploaded files are stored temporarily in server memory, then moved to Azure Blob Storage after consent confirmation. Original files are not persisted on the server.
- **State persistence**: LangGraph conversation state is checkpointed to SQLite at `/app/data/checkpoints.sqlite` (controlled by the `CHECKPOINT_DB_PATH` env var), mounted via the `app_data` Docker volume so state survives container restarts.
- **Data volumes**: All stateful data (PostgreSQL, Qdrant, checkpoints) is stored in named Docker volumes and is not lost on `docker compose down`. Use `docker compose down -v` to wipe everything.
