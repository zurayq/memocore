# MemoCore 🧠

A production-ready personal AI assistant that manages your calendar and tasks
via a WhatsApp-style webhook interface. Built with **FastAPI**, **SQLAlchemy**,
**OpenAI**, and **APScheduler**.

---

## Project Structure

```
memo/
├── memocore/
│   ├── __init__.py
│   ├── main.py              # FastAPI app entry point, lifespan management
│   ├── config.py            # Centralised pydantic-settings config
│   ├── database.py          # Async SQLAlchemy engine + session dependency
│   ├── agent.py             # OpenAI intent parser
│   ├── agent_router.py      # Intent → handler dispatch table
│   ├── scheduler.py         # APScheduler reminder engine
│   ├── models/
│   │   ├── __init__.py
│   │   ├── event.py         # One-time calendar events
│   │   ├── task.py          # To-do / action items
│   │   └── recurring_event.py
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── webhook.py       # Incoming message payload
│   │   ├── intent.py        # ParsedIntent (OpenAI output)
│   │   ├── event.py
│   │   ├── task.py
│   │   └── recurring_event.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── event_service.py
│   │   ├── task_service.py
│   │   └── recurring_event_service.py
│   └── routers/
│       ├── __init__.py
│       └── webhook.py       # POST /webhook endpoint
├── .env.example
├── .gitignore
└── requirements.txt
```

---

## Quick Start (Local Development)

### 1. Prerequisites

- Python 3.12+
- An [OpenAI API key](https://platform.openai.com/api-keys)

### 2. Clone & set up the virtual environment

```powershell
# Navigate to the project root (the memo/ folder)
cd C:\Users\abdul\OneDrive\Desktop\memo

# Create a virtual environment
python -m venv .venv

# Activate it (PowerShell)
.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure environment variables

```powershell
# Copy the example env file
Copy-Item .env.example .env
```

Open `.env` in your editor and fill in:

| Variable | Description |
|---|---|
| `ALLOWED_USER_PHONE` | Your phone number in E.164 format, e.g. `+12025551234` |
| `OPENAI_API_KEY` | Your OpenAI secret key |
| `OPENAI_MODEL` | Model to use (default: `gpt-4o-mini`) |
| `DATABASE_URL` | SQLite (default) or PostgreSQL URL |

### 4. Run the server

```powershell
# From the memo/ directory (project root):
uvicorn memocore.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at:
- **Swagger docs**: http://localhost:8000/docs
- **Webhook endpoint**: `POST http://localhost:8000/webhook`
- **Health check**: `GET http://localhost:8000/webhook/health`

---

## Sending Test Messages

Use `curl` or the Swagger UI at `/docs`:

```bash
# Add an event
curl -X POST http://localhost:8000/webhook \
  -H "Content-Type: application/json" \
  -d '{"from": "+12025551234", "body": "Add a team meeting tomorrow at 3pm"}'

# Add a recurring event
curl -X POST http://localhost:8000/webhook \
  -H "Content-Type: application/json" \
  -d '{"from": "+12025551234", "body": "Remind me every Monday at 9am: standup"}'

# Add a task
curl -X POST http://localhost:8000/webhook \
  -H "Content-Type: application/json" \
  -d '{"from": "+12025551234", "body": "Add task: buy groceries, high priority, due Friday"}'

# Query schedule
curl -X POST http://localhost:8000/webhook \
  -H "Content-Type: application/json" \
  -d '{"from": "+12025551234", "body": "What is on my schedule this week?"}'

# Unauthorised sender (returns ignored immediately)
curl -X POST http://localhost:8000/webhook \
  -H "Content-Type: application/json" \
  -d '{"from": "+19999999999", "body": "Hack the mainframe"}'
```

---

## Supported Intents

| Natural Language | Intent | Handler |
|---|---|---|
| "Add a meeting on Friday at 2pm" | `add_event` | `handle_add_event` |
| "Remind me every Monday at 9am: standup" | `add_recurring_event` | `handle_add_recurring_event` |
| "Add task: buy groceries, high priority" | `add_task` | `handle_add_task` |
| "What's on my schedule this week?" | `query_schedule` | `handle_query_schedule` |
| "Change meeting ID abc123 to 4pm" | `update_event` | `handle_update_event` |
| "Delete event ID abc123" | `delete_event` | `handle_delete_event` |

---

## Switching to PostgreSQL (Production)

1. Install and start PostgreSQL.
2. Create a database: `CREATE DATABASE memocore;`
3. Update `.env`:
   ```
   DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/memocore
   ```
4. For production schema management, use **Alembic** migrations instead of
   the dev-mode `init_db()` auto-create.

---

## Architecture Overview

```
Webhook POST
    │
    ▼
routers/webhook.py
    ├─ Auth check (ALLOWED_USER_PHONE)
    ├─ agent.py (OpenAI → ParsedIntent)
    └─ agent_router.py (dispatch)
            │
            ├─ services/event_service.py
            ├─ services/task_service.py
            └─ services/recurring_event_service.py
                        │
                        ▼
                   database.py (AsyncSession)
                        │
                        ▼
                   models/ (SQLAlchemy ORM)

Background:
    scheduler.py (APScheduler)
        └─ _check_upcoming_events() every 60s
```

---

## Key Design Decisions

| Decision | Rationale |
|---|---|
| **Async throughout** | FastAPI + asyncpg/aiosqlite never block the event loop |
| **Pydantic Settings** | Single validated config object; easy to mock in tests |
| **Services separate from routers** | Services are framework-agnostic; testable without HTTP |
| **Dispatch table pattern** | Adding a new intent = one function + one dict entry |
| **UUID primary keys** | No sequential enumeration risk; works in distributed systems |
| **`reminder_sent` flag** | Prevents duplicate reminders across scheduler ticks |
| **SQLite default** | Zero-setup local dev; swap to PostgreSQL without code changes |
