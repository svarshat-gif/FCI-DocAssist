# FCI AI Circular Assistant

Production-oriented full-stack RAG application for answering questions only from official Food Corporation of India circulars and temporary user-uploaded PDFs.

## Stack

- Frontend: Next.js 15, React, TypeScript, TailwindCSS, shadcn-style components, Framer Motion, Lucide Icons
- Backend: FastAPI, SQLAlchemy, Pydantic, Uvicorn
- Database: PostgreSQL
- Vector store: ChromaDB
- Embeddings: `BAAI/bge-m3`
- LLM: Gemini 2.5 Flash via `google-genai`
- PDF extraction: pdfplumber with PyMuPDF fallback
- Scheduling: APScheduler
- Auth: JWT with bcrypt password hashing

## Key Behavior

- Answers are generated only after retrieval from indexed FCI circulars or the active temporary PDF session.
- Unsupported questions return: `I could not find this information in the indexed FCI Circulars.`
- Responses include citations with circular number, title, publication date, official URL, and page when available.
- Uploaded PDFs are not permanently stored; only temporary embeddings are created and cleaned after expiry.
- The crawler is environment-configured and skips duplicates by official URL and file hash.
- Multilingual responses use Gemini prompting, not Google Translate.

## Run Locally

1. Configure environment:

   ```bash
   cp backend/.env.example backend/.env
   cp frontend/.env.local.example frontend/.env.local
   ```

2. Set these required values:

   ```bash
   GEMINI_API_KEY=your-gemini-key
   JWT_SECRET=a-long-random-secret
   FCI_CIRCULAR_URLS=https://fci.gov.in/
   ```

   Point `FCI_CIRCULAR_URLS` to the official FCI circular or notification index URL you want the crawler to monitor. Multiple URLs can be comma-separated.

3. Start with Docker:

   ```bash
   docker compose up --build
   ```

4. Open:

   - Frontend: http://localhost:3000
   - Backend API docs: http://localhost:8000/docs

## Manual Development

Backend:

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
npm install
npm run dev
```

## Indexing Circulars

The scheduler runs the crawler daily. You can also run it manually after signing in:

```http
POST /api/v1/circulars/crawl
Authorization: Bearer <token>
```

The first embedding run downloads `BAAI/bge-m3`, so initial indexing can take time.

## Security Notes

- Uploads are validated as PDFs and capped by `MAX_UPLOAD_MB`.
- Passwords are bcrypt-hashed.
- JWT expiry is controlled by `ACCESS_TOKEN_EXPIRE_MINUTES`.
- Prompt-injection resistance is handled in the system prompt and by only exposing retrieved source excerpts to Gemini.
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
  public/       Generated hero asset
```
