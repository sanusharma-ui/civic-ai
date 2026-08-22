# Civic AI Frontend

React + Vite frontend for Civic AI.

## Setup

```bash
cd frontend
npm install
copy .env.example .env
npm run dev
```

Open:

- http://localhost:5173

## Environment

Required for backend chat:

```env
VITE_API_BASE_URL=http://127.0.0.1:8000/api
```

Required for Supabase Auth:

```env
VITE_SUPABASE_URL=https://your-project-ref.supabase.co
VITE_SUPABASE_ANON_KEY=your_supabase_anon_public_key
```

Get these from Supabase:

- Project URL: Supabase dashboard > Project Settings > API > Project URL
- Anon public key: Supabase dashboard > Project Settings > API > Project API keys

Supabase Auth settings:

- Enable Email provider.
- Add `http://localhost:5173/auth` to allowed redirect URLs.
- Add the deployed frontend URL when deploying.

## Current Persistence

Supabase Auth is ready. Chat history is currently saved in browser
`localStorage` per user. When database tables are added, replace the storage
helper with Supabase queries without changing the chat UI.
