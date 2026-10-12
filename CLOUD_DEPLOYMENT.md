# Free Cloud Deployment

FCI Doc Assist is prepared for Cloudflare Pages + Render Free + Neon Free.
It has not been published yet. A GitHub repository and your hosting account
connections are still required. The repository is
[svarshat-gif/FCI-DocAssist](https://github.com/svarshat-gif/FCI-DocAssist).
Do not enable paid plans or add payment methods.
An unlimited, permanently free or always-on service cannot be guaranteed.

## Architecture

- Cloudflare Pages serves the exported Next.js interface and proxies `/api/*`.
- Render Free runs the lightweight Python API; no local AI model is downloaded.
- Neon PostgreSQL stores accounts, private conversations, bookmarks, circulars
  and document-search data. Render restarts do not erase these records.
- Gemini 2.5 Flash answers questions; Gemini Embedding 001 prepares document search.
- A GitHub Actions job checks for new circulars daily at 02:17 Asia/Kolkata.

## 1. Accounts and Repository

Create free accounts at [GitHub](https://github.com/), [Neon](https://neon.com/),
[Render](https://render.com/) and [Cloudflare](https://dash.cloudflare.com/).
Connect the suggested GitHub, Neon and Render integrations to let Codex continue
the setup, or use their dashboards. Use the existing `svarshat-gif/FCI-DocAssist`
repository and deploy the current source from its root, keeping `.env`,
`.tools`, `.venv`, `node_modules`, `.next`, `out` and database backups excluded.
The repository's `.gitignore` already excludes these paths.

Your Gemini key is saved locally in the ignored root `.env`, which now selects
Gemini document search and PostgreSQL storage. Do not put the key in
GitHub source, frontend variables or chat. Confirm in Google AI Studio that the
project is eligible for the free tier and has billing disabled. Model metadata
checks accepted the current key; paid/billing status cannot be inferred from it.

## 2. Persistent Database

Create a Neon **Free** project and database, preferably near your Render region.
Use the direct connection string with `sslmode=require`; retain any additional
SSL parameters Neon supplies. Store it as Render's `DATABASE_URL` secret.
The app accepts Neon's `postgresql://` format and enables the `vector` extension
on startup. No separate vector database subscription is needed.

For local administration, store the same URL only in ignored `backend/.env` with:

```dotenv
DATABASE_URL=your-neon-connection-string
EMBEDDING_PROVIDER=gemini
VECTOR_STORE=postgres
CRAWLER_ADMIN_EMAILS=svarsha.t@gmail.com
SCHEDULER_ENABLED=false
CRAWL_ON_START=false
MAX_UPLOAD_MB=5
```

The root `.env` is also loaded, so its saved Gemini key need not be duplicated.
Never commit this file. Existing accounts/history require a PostgreSQL backup
and restore into Neon; selecting a new database does not migrate old records.

## 3. Backend

In Render choose **New > Blueprint**, connect the repository, and select the
root `render.yaml`. It explicitly chooses `plan: free`; do not create a Render
PostgreSQL instance or paid persistent disk. Supply `DATABASE_URL` and
`GEMINI_API_KEY` using Render's secret environment settings. Render generates
the JWT and scheduled-job secrets. Keep these secrets stable across redeploys.

The blueprint selects `backend/Dockerfile.cloud`, PostgreSQL document search,
5 MB uploads, 100 PDF pages, at most 300 text sections per document, 20,000 stored
sections, and at most five newly added circular PDFs per update. It scans the
latest two listing pages (up to 200 records); this is not complete archive coverage.
Quota failures stop an update without switching to a paid provider.

Wait for `/api/v1/health` on the HTTPS Render address to return `{"status":"ok"}`.
Then create your reserved administrator account from a terminal on your computer:

```powershell
cd backend
.venv\Scripts\python.exe scripts/create_admin.py
```

The command uses your ignored database configuration and hidden password prompts.
Production public signup cannot claim an allowlisted administrator address.
Existing accounts are not overwritten. This app does not yet provide email
verification, password-reset emails or managed identity; use strong passwords.

For a fresh environment, install Python 3.12 and `requirements-cloud.txt` first.
For previously stored circulars without PostgreSQL search data, run the following
in bounded batches. This sends their saved text to Google and consumes free quota:

```powershell
.venv\Scripts\python.exe scripts/prepare_existing_documents.py --limit 5
```

## 4. Frontend

In Cloudflare choose **Workers & Pages > Create > Pages > Connect to Git**:

| Setting | Value |
| --- | --- |
| Project name | `fci-doc-assist` (or an available alternative) |
| Root directory | `frontend` |
| Build command | `npm run build:cloud` |
| Build output directory | `out` |
| Build environment | `NODE_VERSION=22` |

Add `API_PROXY_TARGET` as an **encrypted runtime variable/secret** containing
only the HTTPS Render origin, without `/api/v1`. Do this for production and any
preview environment you intend to use, then redeploy. The included Wrangler
configuration manages Pages settings; the encrypted secret remains dashboard-managed.
Never add Gemini keys, JWT secrets or database credentials to Cloudflare.

The included `functions/api/[[path]].ts` handles backend calls. Use Git deployment
or Wrangler, not drag-and-drop upload of `out` alone, which omits the function.
No Next.js server, paid Workers subscription, custom domain or Vercel plan is needed.
Use the provided `pages.dev` address.

## 5. Daily Updates and Cleanup

Add GitHub Actions repository secrets `BACKEND_URL` (HTTPS Render origin) and
`CRAWLER_JOB_TOKEN` (the value generated in Render). Enable the included
`Update FCI Circulars` workflow and run it manually once to seed documents.
It authenticates independently of user logins and reports failures rather than
silently retrying model calls. GitHub schedules can be delayed and private
repositories have an Actions minutes quota; check the free account allowance.

Uploaded PDF bytes are processed transiently, not retained as permanent files.
Search access expires after 60 minutes. Expired search data is excluded immediately;
physical deletion happens during the next maintenance update (normally daily)
or an explicit delete. Saved chats and cited snippets remain until the user deletes
the conversation. Google may retain submitted text under its own free-tier terms.
Every upload requires a separate Google-processing consent checkbox. Do not upload
confidential employee information or other restricted documents.

## Free-Tier Limits

- [Render Free](https://render.com/docs/free): sleeps after 15 minutes of inactivity,
  so first requests can take about a minute. Filesystem storage is temporary.
  Monthly instance-hours, bandwidth and build limits apply. Without a payment
  method, exceeding eligible allowances suspends service/builds rather than charging.
- [Neon Free](https://neon.com/blog/neon-free-plan-1-gb-per-project): currently 1 GB
  storage and 100 CU-hours per project/month. Chat history also uses this space;
  the app's document cap is not a guarantee that every database stays below quota.
- [Cloudflare Free](https://developers.cloudflare.com/workers/platform/pricing/):
  static files and API-function requests have different limits; Functions use
  the Workers free request allowance. Do not enable paid Workers.
- [Gemini pricing](https://ai.google.dev/gemini-api/docs/pricing): free eligibility,
  model quotas and content-use terms apply. Keep billing disabled; the application
  cannot enforce Google's billing configuration. There is no paid-model fallback.

## Release Checks

Before sharing the public address, sign in as the administrator, run an update,
verify a cited answer against an original PDF, upload a non-confidential sample,
check expiry/deletion, and reload a saved conversation. Confirm that a second
account cannot read the first account's history or uploads. Recheck after a Render
restart. Back up Neon data separately; free-tier retention is not a backup policy.

Automated checks cover storage transactions, expiry filters, account isolation,
consent, model failures and proxy behavior. A real Neon connection, deployed Linux
container and browser visual checks are still required before claiming a verified
public deployment.
