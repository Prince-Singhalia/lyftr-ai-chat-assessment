# Resilient AI Chat

A containerized AI chat application featuring multi-provider LLM fallback, SQLite or PostgreSQL conversation persistence, cross-session response caching, and token usage tracking.

## Live Demo

- **Frontend / Live Application:** [lyftr-ai-chat-assessment-frontend.vercel.app](https://lyftr-ai-chat-assessment-frontend.vercel.app/)
- **Backend:** [lyftr-ai-chat-assessment.onrender.com](https://lyftr-ai-chat-assessment.onrender.com)
- **Backend Health Check:** [lyftr-ai-chat-assessment.onrender.com/health](https://lyftr-ai-chat-assessment.onrender.com/health)
- **GitHub Repository:** [Prince-Singhalia/lyftr-ai-chat-assessment](https://github.com/Prince-Singhalia/lyftr-ai-chat-assessment)

## Production Architecture

- **Frontend:** React + Vite, deployed on Vercel.
- **Backend:** FastAPI in Docker, deployed on Render Free.
- **Database:** Neon PostgreSQL for persistent production conversation history; local development uses file-backed SQLite.
- **LLM gateway:** LiteLLM, with Gemini API keys tried in order and Groq as the optional cross-provider fallback.
- **Response cache:** Process-local; entries are not shared across instances and are cleared when the backend restarts.

Render Free instances can sleep after inactivity, so the first request after a quiet period may take longer while the service wakes.

## Overview

Resilient AI Chat provides a React interface backed by a FastAPI service. The backend owns conversation history, constructs each request from the current session, and sends it through an ordered LiteLLM gateway. It can use two independent Gemini credentials and, when configured, fall back to Groq GPT-OSS 20B. Local Docker development persists successful exchanges in a named SQLite volume; production can use PostgreSQL.

The application is intended as a single-instance assessment and development project. It does not provide user accounts, authorization, or multi-tenant isolation.

## Key features

- Ordered Gemini credential attempts (`key_1`, then `key_2`) with an optional independent Groq provider fallback.
- LiteLLM for all model requests, including Gemini and Groq.
- Retryable provider failure handling with sanitized server diagnostics.
- Backend-owned multi-turn memory and isolated session identifiers.
- Cross-session response reuse keyed by model identity and the complete model message list.
- SQLite or PostgreSQL persistence of successful user/assistant exchanges.
- Per-request input and output token metadata, with a documented estimate if provider usage is absent.
- Responsive React chat UI with safe Markdown and response metadata.
- Docker Compose development workflow with a named SQLite volume.

## Architecture

```mermaid
flowchart LR
  Browser[Browser]
  Frontend[React + TypeScript frontend]
  Backend[FastAPI backend]
  Gateway[LLM gateway / LiteLLM]
  Gemini1[Gemini key 1]
  Gemini2[Gemini key 2]
  Groq[Groq GPT-OSS 20B fallback]
  Cache[LiteLLM local cache + response cache]
  Database[Configured database adapter]
  SQLite[(SQLite locally, Docker volume)]
  Neon[(Neon PostgreSQL in production)]

  Browser --> Frontend
  Frontend -->|POST /chat, history GET| Backend
  Backend -->|load / commit exchanges| Database
  Database --> SQLite
  Database --> Neon
  Backend --> Gateway
  Gateway <--> Cache
  Gateway -->|1. key_1| Gemini1
  Gateway -->|2. key_2 after key_1 failure| Gemini2
  Gateway -->|3. after retryable Gemini failures| Groq
```

FastAPI validates the request, retrieves prior session messages from the configured database, and adds the current message and optional system prompt. The gateway first checks the deterministic response cache. On a miss, it tries Gemini keys in order, then optionally tries Groq if both Gemini attempts failed with retryable errors. A successful response and its metadata are committed with the user message in one database transaction. Failed requests are not written to history or the response cache.

See [docs/architecture.md](docs/architecture.md) for detailed request, fallback, and persistence diagrams.

## Technology stack

Verified from the repository manifests and Dockerfiles:

| Area | Technology |
| --- | --- |
| Frontend | React 19.3.1, TypeScript 7.0.2, Vite 8.3.8 |
| Markdown | react-markdown 10.1.0, remark-gfm 4.0.1 |
| Frontend tests | Vitest 5.1.2, Testing Library, jsdom 29.1.1 |
| Backend | Python 3.12, FastAPI 0.115.6, Pydantic 2.12.5, pydantic-settings 2.14.1 |
| LLM integration | LiteLLM 1.108.12 |
| Persistence | Python `sqlite3` for local SQLite and Psycopg 3 for PostgreSQL |
| Containers | Docker multi-stage builds, Docker Compose |
| Backend tests | pytest 8.3.4, HTTPX 0.28.1 |

The frontend uses `latest` version ranges for some development dependencies. The exact versions used by the current lockfile are listed above; use `npm ci` to install those locked versions.

## Repository structure

```text
backend/
  app/                 FastAPI application, routes, schemas, SQLite/PostgreSQL and LLM services
  tests/               Deterministic backend contract and provider tests
  Dockerfile           Multi-stage Python image; honors hosting PORT
  requirements.txt     Pinned backend dependencies
frontend/
  src/                 React app, components, API client, tests and styles
  public/favicon.svg   Project favicon
  Dockerfile           Multi-stage Vite build and Nginx runtime
docs/
  architecture.md      System and request-flow diagrams
  api.md               Endpoint schemas and examples
  demo-script.md       Short assessment walkthrough
  github.md            Suggested public repository profile
  screenshots/         Reserved for genuine, reviewed screenshots
docker-compose.yml     Local backend, frontend and persistent named volume
Makefile               up, down, test and frontend-build targets
.env.example           Placeholder configuration only
```

## Prerequisites

- Git
- Docker Desktop with Docker Compose
- Node.js 22 or later only for running the frontend directly or executing its tests outside Docker
- Python 3.12 only for running the backend directly or executing backend tests outside Docker
- Gemini credentials for live Gemini requests
- A Groq API key only if the independent Groq fallback is enabled

## Quick start

The following commands are for Windows Command Prompt. In PowerShell, the copy and editor commands also work as shown.

```cmd
git clone https://github.com/Prince-Singhalia/lyftr-ai-chat-assessment.git
cd lyftr-ai-chat-assessment
copy .env.example .env
notepad .env
docker compose up --build -d
```

Set `LLM_API_KEYS` to two comma-separated Gemini API keys and choose a supported Gemini model in `LLM_MODEL`. To enable cross-provider fallback, set `FALLBACK_LLM_ENABLED=true` and configure `GROQ_API_KEY`. Keep secrets in `.env`; do not commit it.

Open the frontend at <http://localhost:3000>. Check backend health at <http://localhost:8000/health>. Stop the containers with `docker compose down`; this keeps the named volume and its conversation history.

### Run without Docker

Backend, from PowerShell:

```powershell
Copy-Item .env.example backend/.env
# Edit backend/.env: configure provider keys and set DATABASE_URL=sqlite:///./data/app.db.
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r backend\requirements.txt
Set-Location backend
uvicorn app.main:app --reload
```

Frontend, in a second terminal from the repository root:

```powershell
Set-Location frontend
npm ci
npm run dev
```

The non-Docker default is the file-backed SQLite URL `sqlite:///./data/app.db`. It creates `backend/data/app.db` when run from the `backend` directory. Docker Compose defaults to `sqlite:////data/app.db` and stores it in the named `app_data` volume. PostgreSQL is selected only when `DATABASE_URL` uses a PostgreSQL URL; connection failures fail startup and never switch to memory or SQLite.

## Environment configuration

The application reads environment variables through Pydantic Settings. `.env.example` contains placeholders and safe development defaults; production values belong in the hosting provider’s environment settings.

| Variable | Required | Purpose |
| --- | --- | --- |
| `LLM_API_KEYS` | Yes for live Gemini use | Ordered comma-separated Gemini API keys. Whitespace around entries is trimmed. The API receives one key per call. |
| `LLM_MODEL` | Yes for live Gemini use | LiteLLM Gemini model identifier, for example `gemini/gemini-3.1-flash-lite`. |
| `GROQ_API_KEY` | Optional | Groq credential. Used only when fallback is enabled and both Gemini calls fail retryably. |
| `FALLBACK_LLM_ENABLED` | Optional; defaults to `false` | Enables third-level Groq fallback. |
| `FALLBACK_LLM_MODEL` | Optional | Groq model identifier; default is `groq/openai/gpt-oss-20b`. |
| `DATABASE_URL` | Optional; default depends on runtime | SQLite `sqlite:///./data/app.db` locally or PostgreSQL `postgresql://...` in production. PostgreSQL requires TLS; insecure `sslmode=disable`, `allow`, and `prefer` modes are rejected. |
| `ALLOWED_ORIGINS` | Optional | Comma-separated browser origins allowed by CORS. Set the exact production frontend origin. |
| `VITE_API_BASE_URL` | Optional in local Compose; required for separate production frontend hosting | Backend base URL baked into the Vite build. Do not use a local URL for a public build. |
| `LITELLM_CACHE` | Optional; defaults to `true` | Enables the LiteLLM local cache and the application response cache. |
| `ENABLE_FAILURE_SIMULATION` | Optional; defaults to `false` | Enables `X-Simulate-Failure` for demonstrations/tests. Keep disabled in production. |
| `LLM_API_BASE` | Optional | Custom provider API base when required by the configured LiteLLM provider. |
| `CACHE_DIR` | Optional | Declared for compatibility, but not currently used by the process-memory response cache. |
| `ENVIRONMENT` | Optional | Deployment environment label. |
| `LOG_LEVEL` | Optional | Backend logging level. |

Health requires a reachable configured database (SQLite or PostgreSQL), at least two Gemini keys, and cache initialization. Groq is optional and does not replace the two-key Gemini requirement. Startup creates the schema with idempotent `CREATE TABLE/INDEX IF NOT EXISTS` statements and records schema version 1 in `schema_migrations`; it does not drop or recreate tables.

## API documentation

The API consists of three routes; OpenAPI, Swagger UI, and ReDoc are disabled. See [docs/api.md](docs/api.md) for the full contract.

### `GET /health`

Healthy response (`200`):

```json
{"status":"ok","keys_configured":2,"cache_enabled":true}
```

Returns `503` with `{"detail":"service unavailable"}` if the configured database, two-key requirement, or cache initialization is unhealthy.

### `POST /chat`

Request:

```json
{"session_id":"demo-1","message":"What is a database index?"}
```

Optional `system_prompt` may be included. On success the response contains `session_id`, `reply`, and `metadata` with `resolution_source`, actual `model`, server `latency_ms`, per-request `input_tokens` and `output_tokens`, `key_id`, and `fallback_attempts`.

### `GET /sessions/{session_id}/messages`

Returns successful user and assistant messages oldest first. System prompts are not stored or returned. An unknown or empty session returns `404` and `{"detail":"session not found"}`.

Invalid payloads return `422` with a JSON validation detail. If all providers are unavailable, `POST /chat` returns `503` and `{"detail":"all providers unavailable"}`. Provider exceptions are not returned to clients.

## Caching

The application response cache uses a deterministic key from the configured primary model identity and the complete ordered model message list. That list contains any system prompt, prior turns, and the current message. Session ID and provider credentials are not part of the key, which permits reuse across sessions without sharing responses across different prompts or histories. Cached entries retain the response text, actual responding model, and original token counts; cache metadata reports `LLM_CACHE`, null `key_id`, and zero fallback attempts.

The response cache is process-local, so it is lost on backend restart and is not shared across multiple workers or replicas. Recognized failure simulation requests bypass it. Failed provider attempts are never added to the response cache.

## Conversation persistence

The configured database stores a `messages` table containing an integer ID, session ID, role, content, optional assistant metadata as JSON text, and an ISO-8601 timestamp. Each successful exchange inserts the user and assistant messages transactionally. Failed calls are not persisted. SQLite uses `INTEGER PRIMARY KEY AUTOINCREMENT`; PostgreSQL uses `BIGSERIAL`. Both use the same idempotent startup schema migration, and existing rows are left in place.

Compose mounts the named volume `app_data` at `/data`, with `DATABASE_URL=sqlite:////data/app.db`. `docker compose down` preserves this named volume; `docker compose down -v` deletes it and must not be used for routine development. For Render Free, use Neon PostgreSQL: Render Free filesystems are ephemeral, so SQLite history would be lost on restarts, deploys, or spin-down. The application opens short-lived connections per operation and accepts Neon pooled PostgreSQL URLs.

## Provider fallback

The gateway tries Gemini `key_1`, then Gemini `key_2`. Groq GPT-OSS 20B is attempted only when both Gemini attempts have retryable failures and Groq is enabled and configured. Retryable categories include HTTP 408, 429, 500, 502, 503, and 504, plus network errors and timeouts. Authentication or invalid-model failures are not treated as retryable for the cross-provider step.

`fallback_attempts` counts failed deployments before the response: normally 0 or 1 for Gemini success and 2 for Groq success. `metadata.model` reports the provider model that actually generated the answer. The backend test suite uses deterministic mocked providers; live Gemini and Groq checks are separate and can be affected by provider quotas and outages. A successful mocked test is not evidence of live provider availability.

## Failure simulation

Set `ENABLE_FAILURE_SIMULATION=true` only in a controlled development environment. The header affects the current request and only supports these status values: `429`, `500`, `502`, `503`.

Supported tokens are `key_1=STATUS`, `key_2=STATUS`, `groq=STATUS`, `fallback=STATUS` (Groq alias), and `*=STATUS` (all deployments). Tokens may be comma-separated. Examples for Windows Command Prompt:

```cmd
curl -X POST http://localhost:8000/chat -H "Content-Type: application/json" -H "X-Simulate-Failure: key_1=429" -d "{\"session_id\":\"demo-key2\",\"message\":\"Hello\"}"
curl -X POST http://localhost:8000/chat -H "Content-Type: application/json" -H "X-Simulate-Failure: key_1=503,key_2=503" -d "{\"session_id\":\"demo-groq\",\"message\":\"Hello\"}"
curl -X POST http://localhost:8000/chat -H "Content-Type: application/json" -H "X-Simulate-Failure: key_1=503,key_2=503,groq=503" -d "{\"session_id\":\"demo-all-fail\",\"message\":\"Hello\"}"
```

A provider that is not simulated must make a real LiteLLM request. Simulation does not fabricate a successful assistant reply. Requests with recognized simulation values bypass the response cache.

## Testing

From the repository root:

```powershell
python -m pytest backend/tests -v
Set-Location frontend
npm ci
npm test
npm run build
Set-Location ..
docker compose config --quiet
docker compose run --rm backend pytest -v
```

Backend tests mock provider calls and do not require live API keys. Two PostgreSQL integration tests are skipped unless `TEST_POSTGRES_DATABASE_URL` points to a dedicated disposable PostgreSQL test database; they write and remove test rows. The frontend suite uses Vitest and Testing Library. Live provider diagnostics are manual and should be reported separately from unit-test results.

## Docker operations

```powershell
docker compose up --build -d
docker compose ps
docker compose logs --tail=100
docker compose restart backend
docker compose run --rm backend pytest -v
docker compose down
```

`docker compose down` stops and removes containers/network but retains the named `app_data` volume. Avoid `docker compose down -v` unless permanently deleting local history is intentional. The Makefile also supplies `make up`, `make down`, `make test`, and `make frontend-build`; on Windows without GNU Make, use the Compose and npm commands above.

## Free-tier deployment: Render + Neon + Vercel

This deployment keeps application data in Neon PostgreSQL. Do not use SQLite on a Render Free web service: its local filesystem is ephemeral and is cleared on restart, redeploy, or spin-down. Render Free services also spin down after 15 minutes of inactivity and can take about a minute to wake. See [Render Free service limits](https://render.com/docs/free). Neon connection strings require TLS; copy the pooled URL from the Neon Console and keep its SSL parameters. See [Neon connection guidance](https://neon.tech/docs/get-started/connect-neon) and [pooling guidance](https://neon.tech/docs/connect/connection-pooling).

### 1. Create Neon database

Create a Neon project, database, and application role. In **Connect**, choose the database/role and leave connection pooling enabled for the Render web service. Copy the generated `DATABASE_URL`; its shape is:

```text
postgresql://<role>:<password>@<endpoint>-pooler.<region>.aws.neon.tech/<database>?sslmode=require&channel_binding=require
```

Use the connection string exactly as generated. URL-encode special characters in credentials if you assemble a URL yourself. The application accepts `postgresql://`, `postgres://`, and `postgresql+psycopg://`; when `sslmode` is omitted it adds `sslmode=require`. It rejects SSL downgrade modes (`disable`, `allow`, `prefer`) and never prints the URL. Startup creates tables idempotently; it does not drop existing rows.

### 2. Deploy backend on Render Free

Create a **Web Service** from the GitHub repository and choose the free instance. Set **Root Directory** to `backend`, **Runtime** to Docker, **Dockerfile Path** to `Dockerfile`, and **Health Check Path** to `/health`. The container uses Render's injected `PORT`. Do not attach SQLite or rely on local files for persistence.

Set these runtime environment variables in Render's service settings:

| Variable | Render value |
| --- | --- |
| `DATABASE_URL` | The Neon pooled PostgreSQL URL copied from Neon; format above. Required. |
| `LLM_API_KEYS` | Two Gemini API keys, comma-separated, in primary/secondary order. Required. |
| `LLM_MODEL` | `gemini/gemini-3.1-flash-lite` (or the intended supported Gemini model). Required. |
| `GROQ_API_KEY` | Groq key. Required only if enabling Groq fallback. |
| `FALLBACK_LLM_ENABLED` | `true` when Groq is configured; otherwise `false`. |
| `FALLBACK_LLM_MODEL` | `groq/openai/gpt-oss-20b` (current fallback model). |
| `ALLOWED_ORIGINS` | Exact Vercel production origin, for example `https://your-project.vercel.app`; comma-separate any additional fixed custom domains. |
| `LLM_API_BASE` | Omit unless a provider requires a custom API base. |
| `LITELLM_CACHE` | `true` (the current health check expects cache initialization). |
| `ENABLE_FAILURE_SIMULATION` | `false` in production. |
| `ENVIRONMENT` | `production`. |
| `LOG_LEVEL` | `INFO` (or a supported Python logging level). |
| `CACHE_DIR` | No value required; currently declared but unused by the response cache. |

`PORT` is injected by Render and should not be set manually. Keep the Gemini and Groq values in Render's secret environment fields, never in Git or frontend variables. Health becomes `200` only after the configured database is reachable, two Gemini keys are present, and the cache is initialized. Verify `https://<render-service>.onrender.com/health` after deployment.

### 3. Deploy frontend on Vercel Hobby

Import the repository into Vercel. Set **Root Directory** to `frontend`, **Framework Preset** to Vite, **Build Command** to `npm run build`, and **Output Directory** to `dist`. Add one build environment variable:

| Variable | Value |
| --- | --- |
| `VITE_API_BASE_URL` | The Render backend origin, for example `https://your-service.onrender.com`; no `/chat` suffix. |

Set it for Production (and Preview only if the backend CORS list is configured to allow that preview origin). `VITE_` variables are included in the public frontend bundle, so never put secrets in Vercel frontend variables. After Vercel gives the site its final origin, set that exact HTTPS origin in Render's `ALLOWED_ORIGINS`, redeploy the backend, and test chat plus session history in a browser. CORS is not authentication; this application has no user login or rate limiting.

### 4. Existing SQLite history

Changing `DATABASE_URL` does not copy an existing SQLite file into Neon. To preserve local history, take a backup of the SQLite file/Compose volume, create an empty Neon database, set the Neon URL as `DATABASE_URL` in a trusted local shell, then from `backend` run:

```powershell
python -m app.migrate_sqlite ..\data\app.db
```

Use the actual path to your SQLite file (for Compose, first make a backup/export from the `app_data` volume). The command requires an empty PostgreSQL `messages` table, copies IDs, history, metadata, and timestamps transactionally, and leaves the SQLite source untouched. Keep the backup until history has been verified through `GET /sessions/{session_id}/messages`. Do not paste the database URL into shell history or commit it.

### Free-tier limits and operational notes

- Render Free may sleep after inactivity, wake slowly, or restart. Requests during cold start can be slow.
- Render Free's filesystem is ephemeral; Neon is the durable store. Keep a separate database backup/export and check the current Neon plan's storage, compute, and retention limits.
- The response cache is process-local, so cache entries disappear on backend restarts and are not shared across replicas. Conversation history and token metadata remain in PostgreSQL.
- The app opens short-lived database connections. The Neon pooled endpoint is recommended for connection-heavy deployment environments.
- Vercel Hobby is intended for personal, non-commercial use. Review current [Vercel Hobby terms and limits](https://vercel.com/docs/plans/hobby) before deployment for a business or paid service.
- Free-tier quotas, policies, and service limits can change; confirm them in each provider's current dashboard and documentation before relying on this setup.

## Security

- Store credentials in environment variables or the hosting provider’s secret manager. `.env` and `.env.*` are ignored; `.env.example` contains placeholders only.
- The frontend receives only the backend URL, never provider keys.
- Provider failures are sanitized in server logs and clients receive generic errors.
- Pydantic validates session IDs and message lengths; system prompts are omitted from history.
- CORS should allow only the intended frontend origin. CORS is not authentication.
- Assistant Markdown uses `react-markdown` and `remark-gfm` without `dangerouslySetInnerHTML`; raw HTML is not enabled.
- Set `ENABLE_FAILURE_SIMULATION=false` in production.
- The API has no authentication or rate limiting. Do not expose it to untrusted public traffic without adding appropriate access controls and abuse protections.
- Use PostgreSQL for Render Free; its filesystem cannot persist SQLite. Keep this deployment to one backend instance unless cache coordination is redesigned.

## Limitations

Provider quotas, rate limits, model availability, network conditions, and free-tier restrictions may interrupt inference. Gemini fallback keys may share provider-side capacity or quota limits. Groq is optional and only handles retryable Gemini failures. The response cache is process-local and is cleared by restarts; PostgreSQL persists conversations and token metadata, not response-cache entries. The in-memory cache does not coordinate across replicas. If a provider omits token usage, the application estimates counts from whitespace-separated text rather than claiming exact tokenizer usage.

## Roadmap

Planned possibilities, not implemented features:

- Add authentication and request-level rate limits before broad public exposure.
- Add browser-level end-to-end tests for deployed-origin behavior.
- Evaluate a multi-instance persistence/cache design if horizontal scaling becomes necessary.

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE).

## Maintainer

See the repository owner listed on GitHub for project maintenance and contact information. No separate support email is published here.

## Acknowledgements

This project uses React, Vite, FastAPI, Pydantic, LiteLLM, SQLite, `react-markdown`, `remark-gfm`, Docker, and the Gemini and Groq model APIs. See the respective package manifests for dependency details.
