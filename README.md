# Civic AI

> **Understand your rights. Take your next step.**

Civic AI is a citizen-first workspace for turning difficult civic and legal
questions into clear, practical action. It brings together focused AI agents
for **Right to Information (RTI)** and **consumer rights**, with guided drafts,
structured answers, and a conversational interface built for Indian citizens.

<p align="center">
	<strong>Ask clearly.</strong>&nbsp;&nbsp;•&nbsp;&nbsp;
	<strong>Understand deeply.</strong>&nbsp;&nbsp;•&nbsp;&nbsp;
	<strong>Act confidently.</strong>
</p>

## What is inside

| Experience | What it helps with |
| --- | --- |
| **RTI Agent** | Frame precise information requests, appeals, and follow-ups. |
| **Consumer Rights Agent** | Plan complaint steps, organise evidence, and draft escalation text. |
| **Streaming chat** | Receive responses progressively through Server-Sent Events. |
| **Conversation workspace** | Keep conversations organised by agent with a focused chat UI. |
| **Knowledge layer** | Seeded civic reference material with an isolated retrieval service ready to evolve. |

## How it works

```text
React + Vite
		 │
		 │ REST / Server-Sent Events
		 ▼
FastAPI API
		 │
		 ├── Agent registry ── RTI Agent
		 │                  └─ Consumer Rights Agent
		 ├── Groq model service
		 ├── Retrieval service + knowledge chunks
		 └── SQLite by default / PostgreSQL when configured
```

The frontend uses Supabase Auth when configured. Without Supabase credentials,
you can still enter the built-in demo mode and explore the workspace locally.

## Project layout

```text
.
├── backend/
│   ├── app/
│   │   ├── agents/       # Specialised civic agents and registry
│   │   ├── api/          # FastAPI routes
│   │   ├── services/     # Chat, model, retrieval, and tool services
│   │   └── prompts/      # Domain-specific system prompts
│   ├── data/              # RTI and consumer knowledge sources
│   └── scripts/           # Knowledge seeding and CLI utilities
└── frontend/
		└── src/
				├── components/   # Landing, auth, chat, and profile views
				├── lib/          # API, storage, and Supabase clients
				└── styles/       # Application styling
```

## Quick start

### 1. Start the backend

From the repository root:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Create `backend/.env` and add at least your Groq key:

```env
GROQ_API_KEY=your_real_key
```

Then run the API:

```powershell
uvicorn app.main:app --reload
```

The API will be available at [http://127.0.0.1:8000](http://127.0.0.1:8000).
Interactive docs are available at [/docs](http://127.0.0.1:8000/docs), and the
health check is at [/health](http://127.0.0.1:8000/health).

### 2. Start the frontend

Open a second terminal from the repository root:

```powershell
cd frontend
npm install
copy .env.example .env
npm run dev
```

Open [http://localhost:5173](http://localhost:5173) in your browser.

The frontend `.env` should contain:

```env
VITE_API_BASE_URL=http://127.0.0.1:8000/api
VITE_SUPABASE_URL=https://your-project-ref.supabase.co
VITE_SUPABASE_ANON_KEY=your_supabase_anon_public_key
```

Supabase is optional for local exploration. To enable email authentication,
enable the Email provider in Supabase and add
`http://localhost:5173/auth` to the allowed redirect URLs.

## Useful commands

| Command | Purpose |
| --- | --- |
| `uvicorn app.main:app --reload` | Run the backend in development mode. |
| `npm run dev` | Start the Vite frontend. |
| `npm run build` | Create a production frontend build. |
| `python scripts/seed_knowledge.py` | Load the bundled knowledge sources. |
| `python scripts/chat_cli.py` | Try the backend from a terminal. |

## API surface

The backend exposes:

- `GET /health`
- `GET /api/agents`
- `GET /api/agents/{agent_id}`
- `POST /api/conversations`
- `GET /api/conversations`
- `GET /api/conversations/{conversation_id}`
- `DELETE /api/conversations/{conversation_id}`
- `POST /api/chat`
- `POST /api/chat/stream`

The streaming endpoint emits Server-Sent Events such as `start`, `thinking`,
`block`, `done`, and `error`, allowing the interface to render an answer as it
arrives.

## Development notes

- Local development uses SQLite and creates `backend/civic_ai.db` on startup.
- Set `DATABASE_URL` to a PostgreSQL connection string when a shared database
	is needed.
- Chat history in the frontend is currently persisted in browser `localStorage`
	per user; the backend also stores conversation records locally.
- Keep secrets in environment files. Do not commit API keys or production
	credentials.

## Responsible use

Civic AI provides educational information and drafting support. It is not a
substitute for a qualified lawyer, official government guidance, or the advice
of a consumer-rights professional. Verify deadlines, procedures, and
jurisdiction-specific details with authoritative sources before acting.

## License

No license has been declared for this project yet.
