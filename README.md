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
- **Medical Document Ingestion** — Upload PDFs and images via chat; OpenAI vision models extract structured data and store it in a persistent document vault
- **Real-time Streaming** — WebSocket-based response streaming with live typing indicator
- **Chat History** — Full conversation history per case, browsable in the sidebar
- **WhatsApp Booking** — Patients can continue the same intake and appointment-booking workflow through a Twilio WhatsApp number

### Twilio WhatsApp setup

The WhatsApp webhook is exposed at `POST /webhooks/whatsapp`. In the Twilio Console, open the WhatsApp-enabled sender, set its incoming message webhook to:

`https://YOUR_PUBLIC_HOST/webhooks/whatsapp`

Use HTTP `POST`, and add these values to the backend `.env`:

```dotenv
TWILIO_AUTH_TOKEN=your-twilio-auth-token
VALIDATE_TWILIO_WEBHOOK=true
PUBLIC_BASE_URL=https://your-public-host
```

The sender's WhatsApp number must match the patient's registered `mobile_number` (prefer E.164 format, for example `+919876543210`). The webhook returns TwiML directly, so incoming messages receive the assistant response without a separate outbound Twilio API call. Patients who have no matching account receive a registration prompt. During local development, expose the backend through an HTTPS tunnel such as ngrok and use that public URL in Twilio.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.11 · FastAPI · Uvicorn |
| AI Orchestration | LangGraph · LangChain |
| LLM | OpenAI API (same configured chat/routing and vision models) |
| Embeddings | `sentence-transformers/all-MiniLM-L6-v2` (384-dim), called via a **remote** Hugging Face Inference Endpoint (`HuggingFaceEndpointEmbeddings`) — not run locally, requires `HF_TOKEN` |
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
│   │   ├── llm.py                 # OpenAI text generation (sync + async)
│   │   ├── azure_client.py        # OpenAI vision client for extraction (legacy filename)
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
| **Document Analyzer** | Processes uploaded PDFs and images using OpenAI vision models, extracts structured clinical data, and maps findings to a department |

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

This section is written for a fresh machine that has Docker and Docker Compose installed, pulling this repo for the first time. Follow it in order — steps 3 and 4 are easy to miss and the app will otherwise come up with no way to log in as an admin or invite a doctor.

### Prerequisites

- Docker and Docker Compose
- A Hugging Face account with an access token (**required** — see below)
- An OpenAI API key (optional but strongly recommended — the assistant degrades to generic canned replies without it)
- Azure Blob Storage container (only needed if patients will upload documents)
- An SMTP account and/or a Deepgram/Twilio account (only needed for doctor-invite emails / consult transcription / WhatsApp — see the relevant subsections below)

### 1. Configure Environment

Copy the template and fill it in:

```bash
cp .env.example .env
```

`.env.example` documents every variable with inline comments; the summary below groups them by what actually breaks if you skip them.

**Required — the backend will not start correctly without these:**

| Variable | Why |
|---|---|
| `HF_TOKEN` | **Mandatory.** Embeddings are called via a remote Hugging Face Inference Endpoint (see the Tech Stack table above) — if this is unset, the backend crashes at import time, before the FastAPI app object even exists. Get one from huggingface.co → Settings → Access Tokens. |
| `POSTGRES_PASSWORD` | Used by `docker-compose.yml` for both the `postgres` container and the `backend`'s `DATABASE_URL` — pick a real value, not the `.env.example` placeholder. |
| `JWT_SECRET` | A long random string. If left unset, the app falls back to a **public, insecure** default and logs a loud warning on every startup — fine for a five-minute local test, never acceptable on a real server. |

**Strongly recommended:**

| Variable | Why |
|---|---|
| `OPENAI_API_KEY` | Without it, chat/triage/booking/document-analysis all silently fall back to generic canned responses instead of real LLM output — the app *runs*, but isn't actually useful. `OPENAI_MODEL` (default `gpt-4o`) and the optional `OPENAI_ROUTER_MODEL`/`OPENAI_SUMMARY_MODEL`/`OPENAI_VISION_MODEL` overrides are documented in `.env.example`. |

**Only needed for specific features — safe to leave blank otherwise:**

| Variable(s) | Feature | If left unset |
|---|---|---|
| `AZURE_STORAGE_CONNECTION_STRING`, `AZURE_CONTAINER_NAME` | Patient document upload/vault | Upload attempts fail; everything else works |
| `DEEPGRAM_API_KEY` | Doctor consult transcription, patient voice-to-text input | Those two features fail; everything else works |
| `TWILIO_AUTH_TOKEN`, `VALIDATE_TWILIO_WEBHOOK`, `PUBLIC_BASE_URL` | WhatsApp channel — see the [Twilio WhatsApp setup](#twilio-whatsapp-setup) section above | The WhatsApp webhook doesn't work; the web app is unaffected |
| `DOCTOR_AUTH_*` (SMTP block) | Doctor invite/reset emails — see [step 4](#4-invite-your-first-doctor) below | You'll have to read invite links from server logs instead of emailing them |
| `ENABLE_API_DOCS` | Interactive `/docs`/`/redoc` | Stays disabled by default — leave this alone in production; it exposes the full API schema including admin models |
| `JWT_LEGACY_SECRET` | JWT secret rotation | Only ever set this during a deliberate rotation — see the comment in `.env.example` |

`DATABASE_URL`, `QDRANT_URL`, and `QDRANT_MODE` are already set correctly by `docker-compose.yml` for the Docker path below and do not need to be in `.env`.

### 2. Run with Docker Compose

```bash
docker compose up -d
```

Building the `backend` image also downloads the fastText language-identification model (`models/lid.176.bin`, ~126MB) automatically. If that download fails (e.g. no network access at build time), the build continues anyway and the app falls back to a lower-accuracy, script-based language heuristic — see `app/services/language.py`.

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

On every start, the entrypoint automatically:
1. Waits for PostgreSQL to pass its health check and Qdrant to start
2. Runs Alembic migrations (`alembic upgrade head`)
3. Seeds the doctor roster and appointment slots from the CSV files
4. Populates the Qdrant clinical knowledge base from the clinical dataset

Each of these runs on **every** container start, not just the first — each is self-checking (migrations are idempotent via Alembic's own version table; the CSV seeding is an idempotent upsert; the Qdrant hydration checks the collection's actual point count before re-embedding anything) rather than gated behind a one-time flag file. An earlier version of this gated all four behind `/app/data/.initialized` in the `app_data` volume — that flag lived in a different volume than the actual database data, so if the two ever diverged (a recreated Postgres volume, a different `DATABASE_URL`, a partial earlier deploy), the flag stayed present forever while the doctors/appointment_slots tables silently stayed empty. See `TECH_DEBT.md` for the full writeup.

**Not everything is created at this step.** A handful of tables (the consult/SOAP feature, holidays, revoked-login-tokens, and — unless you set `ADMIN_BOOTSTRAP_ENABLED=true` below — the admin account table) only get created lazily, the first time that specific feature is actually used, not at deploy time. This is intentional; see `TECH_DEBT.md` if you want the full detail.

Confirm the backend is actually up before continuing:

```bash
curl http://localhost:8010/health
# {"status":"ok"}
```

If this doesn't return quickly, check `docker compose logs backend` — the most common first-run failure is a missing/invalid `HF_TOKEN` (see step 1), which crashes the backend container immediately.

The app is available at **http://localhost:8010**

### 3. Create the first admin account

There's no self-service "create the first admin" button in the UI — you need one of these two paths:

**Option A — bootstrap via `.env`, before first boot.** Add these to `.env` *before* running `docker compose up -d` for the first time:
```env
ADMIN_BOOTSTRAP_ENABLED=true
ADMIN_EMAIL=admin@yourhospital.com
ADMIN_PASSWORD=a-strong-password
ADMIN_NAME=Administrator
```
This account is created (and its password re-synced) on every startup while `ADMIN_BOOTSTRAP_ENABLED` stays `true` — a deliberate opt-in, so leaving a stale value here doesn't silently reset a password later. Consider setting it back to `false` after the first successful login.

**Option B — run it directly against an already-running container**, any time after `docker compose up -d`:
```bash
docker compose exec backend python scripts/manage_admin.py --email admin@yourhospital.com --name "Administrator"
# prompts for a password interactively if --password is omitted
```

Either way, log in at **http://localhost:8010** with that email/password to reach the admin panel.

### 4. Invite your first doctor

Doctor accounts are created in two steps from the admin panel: first add the doctor's profile (name/department/experience), then click "Send Invite" and type in *that doctor's* real email address (this is entered live in the UI, not stored in `.env` — see `DOCTOR_AUTH_EMAIL_FROM` below, which is a completely different thing: the *sender* identity, not the recipient).

Before doing this, decide how invite emails actually get delivered:

- **`DOCTOR_AUTH_EMAIL_NO_SEND=true`** (good for a first test) — no email is sent at all; the invite link is only printed to `docker compose logs backend`, e.g. `[doctor-invite:no-send] invite link for doctor@example.com: https://.../doctor/set-password?token=...`. You'd copy that link out of the logs and send it to the doctor yourself.
- **`DOCTOR_AUTH_EMAIL_NO_SEND=false`** (real delivery) — also set `DOCTOR_AUTH_SMTP_HOST`, `DOCTOR_AUTH_SMTP_PORT`, `DOCTOR_AUTH_SMTP_USE_TLS`, `DOCTOR_AUTH_SMTP_USERNAME`, `DOCTOR_AUTH_SMTP_PASSWORD`, and `DOCTOR_AUTH_EMAIL_FROM` to a real SMTP provider (Gmail with an App Password, SendGrid, AWS SES, Mailgun, or your organization's existing Office365/Google Workspace mailbox all work — standard SMTP+STARTTLS on port 587). If SMTP isn't configured while this is `false`, sending an invite fails outright with an error, rather than silently falling back to logging.

Either way, **`DOCTOR_AUTH_FRONTEND_URL` must be your real public domain** (e.g. `https://yourdomain.com`), not `localhost` — this is the base URL baked into every invite/reset link. Also generate a real encryption key for MFA secret storage (a placeholder here is not safe to run with):
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```
and set it as `DOCTOR_AUTH_ENCRYPTION_KEY`.

Once the doctor opens their invite link, they set a password and enroll in MFA (QR code for an authenticator app) in the same flow.

### 5. Local Development (without Docker)

```bash
pip install -r requirements.txt
python scripts/download_language_model.py  # optional — fetches models/lid.176.bin for full-accuracy language detection
# Export the variables from .env into your shell, then:
python run.py
```

> **Note for Windows:** `run.py` sets `WindowsSelectorEventLoopPolicy` automatically to fix the asyncio + aiohttp compatibility issue.

---

## Before Going to Production

This repo has undergone a full security/functionality audit — the complete findings live in `FULL_SYSTEM_AUDIT.md` (and known, intentionally-accepted tech debt in `TECH_DEBT.md`). Do not skip reading it before a real deployment. The short version of what's most likely to bite you:

- **TLS/HTTPS is handled by the `certbot` service + `nginx.conf`'s `:443` block**, obtaining a Let's Encrypt certificate for `165-232-178-215.sslip.io`. That hostname is IP-literal (sslip.io always resolves it to `165.232.178.215`) — whichever host runs this stack **must own that exact IP**, or certificate issuance and HTTPS will fail. `nginx.conf` has a comment with the exact `Strict-Transport-Security` header line to add once HTTPS is confirmed working end-to-end.
- **The admin panel (`/admin`) has no network-layer restriction** — anyone who obtains admin credentials can reach it from anywhere. `FULL_SYSTEM_AUDIT.md` §"P1 #12" has a ready-to-use nginx IP-allowlist snippet.
- **Leave `ENABLE_API_DOCS` unset/`false`** in production — it's off by default for a reason (full schema, including admin models, would otherwise be publicly reachable at `/docs`).
- **`JWT_SECRET` must be a real random value, not left blank.** An unset value falls back to a public, well-known string and logs a warning on every boot — treat that warning as a deploy blocker, not noise.
- The WhatsApp channel's signature validation (`VALIDATE_TWILIO_WEBHOOK`) can be turned off — never do this outside local testing.

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
- **Re-deploying to a new host**: `git pull`/`git clone` does not bring over everything needed to run the stack.
  - `.env` is gitignored and must be copied from the old server manually.
  - The `certbot_certs` Docker volume is local to each host, so a fresh host starts with no certificate. `frontend-entrypoint.sh` serves a temporary self-signed placeholder until the `certbot` service obtains a real one (same bootstrap flow as the original deploy) — this only succeeds if the new host owns the IP that `165-232-178-215.sslip.io` resolves to, so stop the old host (or otherwise release the IP) before/while starting the new one, since Let's Encrypt's HTTP-01 challenge validates against whichever host currently answers on it.
  - `models/lid.176.bin` is also not tracked in git — `docker compose build` re-downloads it via `scripts/download_language_model.py`.
- **State persistence**: LangGraph conversation state is checkpointed to SQLite at `/app/data/checkpoints.sqlite` (controlled by the `CHECKPOINT_DB_PATH` env var), mounted via the `app_data` Docker volume so state survives container restarts.
- **Data volumes**: All stateful data (PostgreSQL, Qdrant, checkpoints) is stored in named Docker volumes and is not lost on `docker compose down`. Use `docker compose down -v` to wipe everything.
