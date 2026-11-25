# Implementation plan

1. Build a separated FastAPI + SQLite backend with explicit configuration, persistence, LiteLLM gateway, cache metadata, failover simulation, and contract tests.
2. Build a responsive Vite React frontend with multi-turn chat, metadata, loading/error states, and runtime backend URL configuration.
3. Add multi-stage Dockerfiles, Compose, Makefile, environment examples, documentation, and deployment templates.
4. Run backend tests and frontend build, inspect the diff, and commit coherent milestones.
