# Security policy

## Supported deployment practices

- Keep provider credentials in environment variables or a hosting secret manager; never expose them to the browser.
- Keep `.env` out of Git and use placeholders in `.env.example`.
- Set `ENABLE_FAILURE_SIMULATION=false` in production.
- Restrict `ALLOWED_ORIGINS` to the intended frontend origin. CORS is not access control.
- Use HTTPS and persistent protected storage for `/data`.
- The application currently has no authentication, authorization, or rate limiting. Do not expose it to untrusted public traffic without adding appropriate controls.

## Reporting a vulnerability

Please report security issues privately through GitHub Security Advisories for this repository when that feature is available. If private advisories are unavailable, contact the repository owner through their GitHub profile and avoid posting exploit details publicly. Do not include API keys, access tokens, personal data, or production secrets in a report.

No security response-time guarantee is provided.
