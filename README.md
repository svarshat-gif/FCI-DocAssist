# FCI Doc Assist

Document assistant for official Food Corporation of India circulars and temporary user-uploaded PDFs, with private saved chats and summaries. Use [CLOUD_DEPLOYMENT.md](CLOUD_DEPLOYMENT.md) for the selected free cloud setup: Cloudflare Pages, Render Free, Neon PostgreSQL and Gemini. [DEPLOYMENT.md](DEPLOYMENT.md) covers local hosting alternatives.

## Stack

- Frontend: Next.js 15, React, TypeScript, TailwindCSS, shadcn-style components, Framer Motion, Lucide Icons
- Backend: FastAPI, SQLAlchemy, Pydantic, Uvicorn
- Database: PostgreSQL
- Document search: PostgreSQL with pgvector and Gemini Embedding 001 on the cloud setup
- Optional local search: ChromaDB and `BAAI/bge-m3`
- LLM: Gemini 2.5 Flash via `google-genai`, with optional local Ollama mode
- PDF extraction: pdfplumber with PyMuPDF fallback
- Scheduling: APScheduler
- Auth: JWT with bcrypt password hashing

## Key Behavior

- Answers are generated only after retrieval from indexed FCI circulars or the active temporary PDF session. Retrieval, strict prompts and citation validation reduce hallucination risk; generated answers should still be checked against the linked originals.
- Unsupported questions return: `I could not find this information in the available FCI circulars.`
- Responses include citations with circular number, title, publication date, official URL, and page when available.
- Uploaded PDF bytes are not permanently stored; document access expires after one hour. Expired search data is removed by maintenance, daily on the cloud setup and every 15 minutes with the local scheduler. Conversation messages and cited snippets remain in the user's private history until cleared.
- The crawler is environment-configured and skips duplicates by official URL and file hash.
- Ten-language interface labels are bundled with the app, so switching the interface uses no API quota. Multilingual answers use the configured AI model, not Google Translate.
- Authentication protects conversations, uploads, summaries, bookmarks and exports. A separate administrator email allowlist controls manual crawling.
- Chat history supports title search, older-chat pagination and private saved summaries. Opening a chat keeps its address in the browser so refreshing restores it; history is stored in PostgreSQL, not browser storage.
- Answers are checked before NDJSON delivery; the browser receives source metadata before generated text. This is validated response delivery, not unverified live model tokens.

## Run Locally

Use a Compose-compatible container runtime, then:

```powershell
powershell -File scripts/setup.ps1 -Provider gemini
docker compose up --build -d
```

The setup script stores your API key and generated secrets in the ignored **root `.env`**, which Compose reads. Keep billing disabled on the Gemini project to use its eligible free tier. To avoid any AI API key, use `-Provider ollama` and follow [the local AI commands](DEPLOYMENT.md#start-on-windows).

Open http://localhost:3000. API docs: http://localhost:8000/docs.

## Manual Development

Backend:

Start PostgreSQL and configure `backend/.env` from `backend/.env.example` before starting the backend. Use a random JWT secret and a valid database connection string.

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload
```

Frontend:

```bash
cd frontend
npm ci
npm run dev
```

## Indexing Circulars

The scheduler runs the crawler on startup and daily at 02:00 Asia/Kolkata. The crawler reads FCI's public dynamic listing API, including PDF attachments and official PDF links in descriptions, then checks configured HTML pages. It excludes future publications and scans at most `CRAWLER_MAX_PAGES` API pages of 100 records (default 40). Increase the cap for older archives. Manual updates require an account whose email appears in `CRAWLER_ADMIN_EMAILS`:

```http
POST /api/v1/circulars/crawl
Authorization: Bearer <token>
```

Local search downloads `BAAI/bge-m3` on first use. The selected cloud setup instead uses Gemini for document search, disables the built-in scheduler, and updates through GitHub Actions at 02:17 Asia/Kolkata. Each update adds at most five new PDFs by default. Settings also provides a manual update action.

## Verification

```powershell
cd backend
pip install -r requirements-dev.txt
python -m pytest tests -q
python -m compileall -q api crawler database embeddings models rag routers scheduler services utils main.py
```

```powershell
cd frontend
npm ci
npm run typecheck
npm run build
```

Backend tests use an isolated in-memory database with a test-only JSONB compiler and mocked AI/retrieval boundaries. They cover account isolation, upload ownership, fail-closed answers, stream delivery, follow-up memory, bookmarks, summaries, exports, public-listing pagination and Gemini error handling. They do not prove live Gemini or BGE-M3 quality. Follow the real-service checklist in [DEPLOYMENT.md](DEPLOYMENT.md#verify-the-real-services) before public use.

The frontend production/static builds and backend tests have passed locally. The public FCI listing and an official PDF download were checked live. Google's model metadata checks accepted the saved key. Live Neon integration, the Linux container deployment, and browser visual QA are not yet verified; the app has not been published. Local Chroma testing was blocked by Windows application-control policy on a native dependency.

## Security Notes

- Uploads are validated as PDFs and capped by `MAX_UPLOAD_MB`.
- Passwords are SHA-256 prehashed before bcrypt, preserving long and Unicode passwords. Legacy bcrypt hashes remain verifiable.
- JWT expiry is controlled by `ACCESS_TOKEN_EXPIRE_MINUTES`.
- The system prompt treats retrieved source text as untrusted and requires supported source IDs. This does not constitute a guarantee against every prompt injection or factual error.
- Secrets must be provided through environment variables.

## Project Layout

```text
backend/
  api/          FastAPI dependencies
  crawler/      FCI discovery and indexing
  database/     SQLAlchemy engine and initialization
  embeddings/   BGE-M3 embedding wrapper
  models/       ORM and Pydantic schemas
  rag/          Prompts, retrieval, Chroma access
  routers/      API routes
  scheduler/    APScheduler jobs
  services/     Business logic
  utils/        Config, security, PDF/text utilities

frontend/
  app/          Next.js app routes
  components/   Landing, chat, layout, and UI components
  contexts/     Auth and theme state
  hooks/        Reserved for shared hooks
  lib/          API client, types, utilities
  public/       Paper texture and self-hosted fonts
```
