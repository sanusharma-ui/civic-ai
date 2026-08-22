# Civic AI Backend

FastAPI backend for Civic AI. It currently supports two modular agents:

- `rti` - RTI Agent
- `consumer` - Consumer Rights Agent

The backend uses Groq for LLM responses, keeps chat state in memory for now,
and keeps retrieval isolated behind `RetrievalService` so Supabase, RAG,
official sources, and embeddings can be added later.

## Setup

```bash
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

Edit `.env` and set:

```env
GROQ_API_KEY=your_real_key
```

## Run

```bash
uvicorn app.main:app --reload
```

API docs:

- http://127.0.0.1:8000/docs
- http://127.0.0.1:8000/redoc

## Endpoints

- `GET /health`
- `GET /api/agents`
- `GET /api/agents/{agent_id}`
- `POST /api/conversations`
- `GET /api/conversations`
- `GET /api/conversations/{conversation_id}`
- `DELETE /api/conversations/{conversation_id}`
- `POST /api/chat`
- `POST /api/chat/stream`

## Streaming

`POST /api/chat/stream` returns Server-Sent Events:

```text
data: {"type":"start",...}
data: {"type":"token","token":"Hello"}
data: {"type":"done",...}
```

The frontend can append each `token` as it arrives for a ChatGPT-like typing
experience.
