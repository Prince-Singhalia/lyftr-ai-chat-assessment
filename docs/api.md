# API reference

The application exposes three routes. Swagger, ReDoc, and OpenAPI are disabled. JSON examples below follow the Pydantic request and response schemas.

## `GET /health`

Healthy response (`200`):

```json
{
  "status": "ok",
  "keys_configured": 2,
  "cache_enabled": true
}
```

Health is `503 {"detail":"service unavailable"}` if the configured database is unreachable, fewer than two Gemini keys are configured, or caching is disabled/uninitialized.

## `POST /chat`

Request fields:

| Field | Type | Rules |
| --- | --- | --- |
| `session_id` | string | Required, trimmed, 1–128 characters |
| `message` | string | Required, trimmed, 1–4000 characters; whitespace-only is rejected |
| `system_prompt` | string or null | Optional; applies to this request and is not stored in returned history |

Example request:

```json
{
  "session_id": "demo-session-42",
  "message": "Explain a database index in one paragraph.",
  "system_prompt": "Be concise and clear."
}
```

Example response:

```json
{
  "session_id": "demo-session-42",
  "reply": "A database index is a lookup structure...",
  "metadata": {
    "resolution_source": "LIVE_INFERENCE",
    "model": "gemini/gemini-3.1-flash-lite",
    "latency_ms": 742,
    "input_tokens": 24,
    "output_tokens": 38,
    "key_id": "key_1",
    "fallback_attempts": 0
  }
}
```

The values above are illustrative and not a recorded benchmark. On a cache hit, `resolution_source` is `LLM_CACHE`, `key_id` is null, `fallback_attempts` is zero, and the cached response's actual model and token counts are retained. A Groq response reports `groq/openai/gpt-oss-20b` as its model.

Responses:

- `200`: inference or response-cache hit.
- `422`: malformed JSON or Pydantic validation failure, returned as JSON.
- `503`: `{"detail":"all providers unavailable"}` when inference has no successful provider; no failed exchange is stored.

## `GET /sessions/{session_id}/messages`

Returns messages oldest first:

```json
{
  "session_id": "demo-session-42",
  "messages": [
    {"role": "user", "content": "Hello", "metadata": null},
    {
      "role": "assistant",
      "content": "Hello! How can I help?",
      "metadata": {
        "resolution_source": "LIVE_INFERENCE",
        "model": "gemini/gemini-3.1-flash-lite",
        "latency_ms": 742,
        "input_tokens": 4,
        "output_tokens": 7,
        "key_id": "key_1",
        "fallback_attempts": 0
      }
    }
  ]
}
```

An unknown session (including one with no successful exchanges) returns `404 {"detail":"session not found"}`. System prompts are not stored or returned.

## Failure simulation header

When `ENABLE_FAILURE_SIMULATION=true`, `X-Simulate-Failure` accepts comma-separated values such as `key_1=429`, `key_2=500`, `groq=503`, `fallback=503` (Groq alias), or `*=429` (all providers). Only statuses 429, 500, 502, and 503 are accepted for simulation. Simulated requests bypass the application response cache, and unsimulated successful deployments still make real LiteLLM calls.
