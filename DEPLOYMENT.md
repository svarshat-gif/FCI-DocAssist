# Free Setup and Deployment

For the selected Cloudflare Pages + Render Free + Neon setup, start with
[CLOUD_DEPLOYMENT.md](CLOUD_DEPLOYMENT.md). The instructions below describe the
optional local-container setup, not the cloud architecture.

The software has no subscription requirement. The reliable zero-hosting-fee option
is to run it on a computer you already own. Hardware, internet and electricity are
still required. Free API quotas and third-party hosting terms can change; an
unlimited, permanently free, always-on cloud deployment is not promised.

## Choose AI Mode

| Mode | Credential | Cost and limits |
| --- | --- | --- |
| Gemini | Google AI Studio API key | Free-tier requests only when your Google project is eligible and billing is disabled. Quotas apply. |
| Ollama | None | Runs a local model; no inference API charges. Requires more RAM and disk. |

The default remains Gemini 2.5 Flash. Ollama is an optional alternative for
avoiding external API fees. It does not silently replace Gemini when quota runs
out. Local model accuracy and language quality depend on the chosen model.

Official terms: [Gemini pricing](https://ai.google.dev/gemini-api/docs/pricing),
[Ollama](https://ollama.com/).

## Required Details

- Gemini mode: create a key in [Google AI Studio](https://aistudio.google.com/apikey).
  Keep billing disabled to stay on the free tier. Enter the key in the setup
  script's hidden prompt, or in `GEMINI_API_KEY` in the ignored root `.env`.
  Do not paste API keys into chat or commit them.
- Your account email: used by `CRAWLER_ADMIN_EMAILS` to allow manual indexing.
  Configured as `svarsha.t@gmail.com`. Production signup reserves allowlisted
  addresses. Run `docker compose exec backend python scripts/create_admin.py`
  before sharing the app. There is no default password or email-verification
  service; use the hidden password prompt.
- The official FCI circular listing URL(s) you want monitored. Set
  `FCI_CIRCULAR_URLS` to comma-separated HTTPS `fci.gov.in` URLs. Official PDF URLs
  are also accepted. FCI's public dynamic listing is supported automatically,
  including official PDF links inside descriptions. No FCI API key is needed.

PostgreSQL, Chroma and embeddings are local services. They need no paid API key,
hosted database subscription, Firebase, or Supabase account.

## Start on Windows

Install a compatible Compose container runtime. Docker Engine on Linux is free;
Podman Desktop is a free alternative on Windows. Docker Desktop has its own
licensing rules, so do not assume enterprise use is free. The commands below use
`docker compose`; Podman users can use their configured `podman compose` provider.

For Gemini:

```powershell
powershell -File scripts/setup.ps1 -Provider gemini
docker compose up --build -d
```

For local AI without any API key:

```powershell
powershell -File scripts/setup.ps1 -Provider ollama
docker compose --profile local-ai up --build -d
docker compose exec ollama ollama pull qwen3:4b
```

Open http://localhost:3000. The backend documentation is at
http://localhost:8000/docs. The first indexing run downloads BGE-M3 and can take
several minutes. Allow roughly 16 GB RAM for comfortable CPU use with both BGE-M3
and a local generative model; requirements vary with document size and model.

The setup script generates separate database and JWT secrets and preserves an
existing `.env`. Compose reads **the root `.env`**; `backend/.env` is only for a
manual backend process. No secrets are included in either container image.

This workspace already has a root `.env` with generated database/JWT secrets,
your administrator email and the saved Gemini key. Start Compose for local use.
If PowerShell blocks scripts, do not change security policy: configure `.env`
directly, using the existing generated secrets or administrator-approved setup.

Gemini calls use structured JSON, a bounded output size and an HTTP timeout.
Automatic retries and paid-model fallbacks are disabled. A quota error returns
HTTP 429 rather than switching providers. The app cannot determine whether your
Google project has billing enabled; confirm that yourself in Google AI Studio.

## Share a Temporary Free URL

```powershell
docker compose --profile share up -d share
docker compose logs share
```

Open the `https://...trycloudflare.com` URL from the logs. The frontend proxies
API calls on the same origin, so visitors never call their own `localhost`.
This uses a Cloudflare Quick Tunnel and requires no account or domain.

This is a testing/demo deployment: the computer and containers must remain on,
the URL changes after recreation, and there is no uptime guarantee. The app uses
NDJSON delivery rather than SSE, which Quick Tunnels do not support. See
[Cloudflare's limits](https://developers.cloudflare.com/tunnel/get-started/quick-tunnels/).

For a stable production hostname, use a managed tunnel and a domain you already
own, or deploy the Compose services on infrastructure you control. A newly
purchased domain or paid server would no longer meet a strict zero-cost budget.

## Verify the Real Services

1. Register an account, sign out and sign in again.
2. Under Settings, update circulars using the configured administrator account.
   Confirm that documents were actually indexed. Review crawler logs if none
   were discovered; the public frontend protocol may have changed.
3. Search for an indexed circular and open its original PDF.
4. Ask a question, verify the cited page against that PDF, then ask a follow-up.
5. Try an unrelated question; it must return the not-found response.
6. Save a bookmark, reload, and check that it remains available.
7. Summarize a circular and export the saved conversation in PDF and TXT.
8. Upload a PDF, check that a new chat uses only that PDF, then start a new chat
   to return to official sources. Upload collections expire after one hour and
   are deleted by the cleanup job (every 15 minutes).

PDF bytes are never written to permanent storage. Chat messages and cited
snippets are saved as conversation history until the user clears it. In Gemini
mode, retrieved excerpts are sent to Google; its free tier may use content to
improve products under its terms. Use local AI for documents that must stay local.

## Maintenance

```powershell
docker compose logs backend
docker compose logs frontend
docker compose down
```

`down` preserves database, vector and model-cache volumes. Back up PostgreSQL and
Chroma together. Do not run `down -v` unless you intend to erase stored data.
Run a single backend instance for the built-in scheduler and local Chroma store;
multiple replicas require a shared vector service and a dedicated scheduler.
