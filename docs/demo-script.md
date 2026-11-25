# Demo script (2–3 minutes)

This walkthrough is for a deployed environment after its URLs and provider configuration have been verified. Do not display `.env`, credentials, or private account information.

1. Open the public frontend. Send a short question and point out `LIVE_INFERENCE`, model, latency, and token counts.
2. Ask a follow-up that relies on the first answer. Explain that the backend reconstructed the session history from SQLite.
3. Open a fresh tab/session and repeat the first prompt. Point out `LLM_CACHE`, identical answer, preserved tokens, null key ID, and zero fallback attempts.
4. Send a request using `X-Simulate-Failure: key_1=429`. Show the response metadata for `key_2` and one fallback attempt. The second call is real.
5. With Groq enabled, simulate both Gemini failures using `key_1=503,key_2=503`. Show a real Groq response and its model metadata.
6. Simulate all providers using `*=429`. Show the generic 503 and verify that the failed session has no history.
7. Show the history endpoint, running Docker services and persistent volume, then the public repository.

Example commands for Windows Command Prompt (replace only the base URL after deployment):

```cmd
curl -X POST %BACKEND%/chat -H "Content-Type: application/json" -H "X-Simulate-Failure: key_1=429" -d "{\"session_id\":\"demo-key2\",\"message\":\"Explain a database index\"}"
curl -X POST %BACKEND%/chat -H "Content-Type: application/json" -H "X-Simulate-Failure: key_1=503,key_2=503" -d "{\"session_id\":\"demo-groq\",\"message\":\"Reply briefly\"}"
curl -X POST %BACKEND%/chat -H "Content-Type: application/json" -H "X-Simulate-Failure: *=429" -d "{\"session_id\":\"demo-failed\",\"message\":\"This should fail cleanly\"}"
curl %BACKEND%/sessions/demo-failed/messages
```

The simulated all-provider request should return `503 {"detail":"all providers unavailable"}`; the final history request should return 404.
