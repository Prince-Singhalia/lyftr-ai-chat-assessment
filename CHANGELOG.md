# Changelog

This changelog records implemented work reflected in the repository history. There are no tagged releases or version numbers yet.

## Unreleased

### Added

- FastAPI chat API with SQLite session history and transactionally stored successful exchanges.
- Ordered Gemini credential attempts with optional Groq GPT-OSS 20B fallback through LiteLLM.
- Deterministic response caching, per-response token metadata, and failure simulation for provider testing.
- Responsive React/TypeScript chat frontend with safe GitHub-style Markdown rendering.
- Multi-stage Docker images, Compose development workflow, persistent SQLite volume, backend tests, and frontend tests.
- API, architecture, setup, security, contribution, and demonstration documentation.

### Changed

- Backend container honors the hosting platform `PORT` environment variable.
- LiteLLM and compatible Pydantic dependencies updated to eliminate the observed cache runtime compatibility error.
