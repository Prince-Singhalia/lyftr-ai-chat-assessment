# Resilient AI Chat

## 1. Live URLs

No public URLs are claimed in this workspace. Deployment requires provider credentials and hosting accounts; the included Docker and deployment configuration is ready for Render/Vercel-style deployment.

## 2. Run locally: with Docker and without

Copy `.env.example` to `.env`, set at least two real provider keys and a supported LiteLLM model, then run `make up`. The frontend is at `http://localhost:3000` and backend at `http://localhost:8000`. Stop with `make down`.

Without Docker: create a Python 3.12 virtual environment, run `pip install -r backend/requirements.txt`, then `cd backend && uvicorn app.main:app --reload`; in a second terminal run `cd frontend && npm install && npm run dev`.

## 3. Design decisions: key fallback, caching, SQLite session storage

FastAPI owns history and sends only the reconstructed system prompt, prior turns, and new user message to LiteLLM. The gateway iterates an ordered, secret-free key pool and retries the next key after provider errors. A deterministic cache key contains model and full messages, so identical prompts can be reused across sessions without mixing histories. LiteLLM's cache is initialized at startup, while the small cache service preserves response metadata and makes cache-hit classification deterministic. SQLite is mounted at `/data/app.db`; exchanges are committed transactionally only after a successful completion.

## 4. Verification: how to see failover, cache hits and per-message token usage

`curl http://localhost:8000/health`

`curl -X POST http://localhost:8000/chat -H "Content-Type: application/json" -d '{"session_id":"demo","message":"Hello"}'`

Send the same JSON with a different session ID to see `LLM_CACHE`, `key_id: null`, and retained token counts. To test failover, add `-H "X-Simulate-Failure: key_1=429"`; the response should identify `key_2` and `fallback_attempts: 1`. Add `-H "X-Simulate-Failure: *=429"` to receive a clean 503 without stored history. History: `curl http://localhost:8000/sessions/demo/messages`.

## 5. Setup Used

React, TypeScript, Vite, FastAPI, Pydantic, LiteLLM, SQLite, Docker Compose, pytest, and the Fetch API. AI coding tool/editor: OpenAI Codex desktop environment. No real provider credentials are committed.

## 6. Bonus features (if any)

Runtime-configurable frontend API base URL, compact metadata presentation, responsive mobile layout, health checks, non-root backend container, and a deterministic failure-simulation header for assessment demonstrations.

### Architecture

The browser calls the FastAPI API. FastAPI validates requests, loads session messages from SQLite, calls the LiteLLM gateway, and commits the user/assistant pair after a successful response. Docker Compose provides the frontend, backend, and persistent named volume.

### Project structure

`backend/app` is split into configuration, database, schemas, routes, cache, token, and LLM gateway services. `frontend/src` separates the chat view, message/input/status components, API client, types, and CSS.

### Deployment and security

Build `backend/Dockerfile` on a platform with a persistent disk mounted at `/data`; set `DATABASE_URL=sqlite:////data/app.db`, two secret keys, the model, and exact frontend origin. Build the frontend with `VITE_API_BASE_URL` set to the backend HTTPS URL. Configure CORS to that exact frontend URL. Secrets, local databases, and cache files are ignored by Git. Public deployment and GitHub publishing remain manual because no hosting or repository credentials are available in this workspace.

### Known limitations

The included cache service is process-local; use one backend instance for the SQLite/process-local cache design or replace it with a supported persistent LiteLLM cache only if the assessment constraints are relaxed. Provider usage is preferred; when absent, the documented whitespace-token estimate is used.

### Demo script (2–3 minutes)

1. Open the deployed frontend and send a first question; point to `LIVE_INFERENCE`, model, latency, and token metadata.
2. Ask a follow-up; explain that the backend reconstructed prior turns.
3. Start a fresh session and send the same first question; show `LLM_CACHE`, identical reply, retained tokens, and null key ID.
4. Use the API client with `X-Simulate-Failure: key_1=429`; show a real response from key 2 and fallback count 1.
5. Use `X-Simulate-Failure: *=429`; show the clean 503 and verify no history was written.
6. Open the history endpoint and show the Docker/project structure.

