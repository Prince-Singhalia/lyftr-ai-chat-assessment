# Contributing

Thanks for helping improve Resilient AI Chat. Changes should preserve the existing API contract, provider fallback order, and SQLite history.

## Development setup

1. Copy `.env.example` to `.env` and configure local provider credentials only if live inference is needed. Never commit `.env`.
2. Start services with `docker compose up --build -d`, or follow the separate backend/frontend instructions in the README.
3. Keep changes focused and update documentation when API behavior, configuration, or operations change.

## Branches and commits

Use a short descriptive branch name, for example `fix/cache-key-isolation` or `docs/local-setup`. Use Conventional Commit messages such as `feat(api): add request field` or `docs: clarify provider setup`.

## Tests

Before opening a pull request, run:

```powershell
python -m pytest backend/tests -v
Set-Location frontend
npm ci
npm test
npm run build
Set-Location ..
docker compose config --quiet
```

Add deterministic provider mocks for unit tests. Label and report any real provider integration check separately; provider outages must not be hidden by mocks.

## Pull request checklist

- [ ] The change is scoped and preserves existing API fields unless an API change is explicitly intended.
- [ ] Backend and frontend tests pass.
- [ ] Documentation and `.env.example` match the implementation.
- [ ] No `.env`, keys, database files, logs, or generated build artifacts are staged.
- [ ] Provider failure and failed-history behavior are covered where relevant.

## Secret handling

Use local environment variables or a secret manager. Never paste credentials into source, issue reports, pull requests, screenshots, logs, or test fixtures. Test fixtures must use synthetic values only.
