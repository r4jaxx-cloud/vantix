# VANTIX — free-services integration build

This package implements the World & Markets site, account features and optional free-tier AI adapters. It is **not deployed or verified for a full public launch**. External accounts and browser validation are still required. No credentials are included.

## Run locally

Python 3.11+; no third-party Python packages required:

```sh
python3 server.py
```

Open http://localhost:8000. Local account registration returns a test verification link when email is not connected. The local database is created on first use. Never expose this development mode to the public internet. Existing users must sign in again because session tokens are now hashed.

## Implemented

- 23 page routes, with public-source context panels throughout.
- Public adapters: Binance crypto snapshots; ECB daily FX via Frankfurter; Federal Reserve and EIA releases; USGS earthquake reports; annual World Bank indicators; SEC filings by CIK with owner contact configured.
- No fabricated numbers or headlines when providers fail. Missing token-security evidence remains UNKNOWN. GoPlus now returns individual provider flags for Ethereum and BNB Chain; it never produces a SAFE verdict. DEX Screener pair lookups cover BNB Chain, Ethereum and Solana. GDELT adds indexed publisher headline links, with indexing time explicitly separate from publication time. Equity prices, complete global news coverage, external social streams and background alert delivery are not implemented.
- Email verification, cookie sessions, password reset/resend and display names.
- Account-scoped watchlist, portfolio quantities and price thresholds. Threshold notifications are evaluated while the alerts page is open against fresh tracked crypto snapshots; they are not an always-on monitoring service.
- Community posts/comments, labels, likes, reports and owner moderation. Feed polling is every 10 seconds while visible; this is a discussion feed, not private live messaging.
- Owner metrics distinguish opted-in page views from authenticated actions. Account and analytics events older than 30 days are purged during periodic active-service maintenance.
- Turso/libSQL remote database adapter. Production startup refuses local-only SQLite. Remote protocol is fixture-tested, not connected to a real account.
- AI: OpenRouter `openrouter/free`, optional Groq `openai/gpt-oss-20b`, optional Gemini `gemini-2.5-flash-lite`; NVIDIA `meta/llama-3.1-8b-instruct` in development only. Keys and explicit free-account flags are required.
- AI receives the user-confirmed question plus matching retrieved public data only. It validates cited source IDs, labels interpretation and offers source search without AI. Citation validation does not prove model accuracy.
- Daily AI caps: 10 requests per user, 20 attempts per provider across the site. Maximum two simultaneous AI requests and three provider attempts per question. No paid model routing or account upgrades.
- Request bounds, network timeouts, shared data caching and one refresh per source. These reduce overload risk; they do not establish a tested visitor capacity.

## Free pilot deployment

`render.yaml` configures a free Python web service. Render says free web services are not intended for production: they sleep after 15 minutes idle, take roughly one minute to wake, have ephemeral files and monthly quotas, and may be suspended for high outbound API/database traffic. This is a **pilot option**, not the requested guarantee of continuous service for many visitors.

1. Put this directory in a private Git repository and connect it to a Render Blueprint, selecting only the free plan.
2. Create a free Turso database and obtain its URL/token. Configure `LIBSQL_URL` and `LIBSQL_AUTH_TOKEN` privately in Render. The app creates its tables on startup.
3. Configure a Brevo account and verified sender. Enter `BREVO_API_KEY`, `MAIL_FROM`, `SUPPORT_EMAIL` and `ADMIN_EMAILS`. Confirm the account remains on its free plan. Sender verification and email deliverability must be tested.
4. Set `VANTIX_PUBLIC_URL` to the actual HTTPS origin, and set `SEC_USER_AGENT` to `VANTIX` plus your real contact email.
5. Optionally create API keys in your own OpenRouter, Groq or Gemini accounts. Set the corresponding enable flags from `.env.example` only after confirming account eligibility, free-tier limits and billing settings. Keys alone do not prove free billing. NVIDIA free hosted prototyping access is disabled in production.
6. Confirm free plans, disable automatic paid upgrades/top-ups and avoid adding a payment method where the provider supports a strictly free account. Set `FREE_ACCOUNTS_CONFIRMED=1`. Quota exhaustion may stop features; the application cannot control provider billing settings.
7. Run `python3 preflight.py`. Then test actual database persistence across a restart, email verification/reset, AI requests, browser flows and expected traffic against the deployed pilot before inviting the public.

No hosting, database, email or AI accounts are connected in this package. No live URL has been created. Do not paste API keys into chat or commit them to the repository.

## Verification

```sh
python3 test_backend.py
python3 test_free_data.py
python3 test_launch.py
python3 test_operations.py
node test_ui.cjs
```

118 checks pass locally: 46 backend checks, 11 public-data fixtures, 17 launch/provider tests, 9 operations/report/source tests and 35 interface-logic checks. Interface tests use a simulated DOM, not a browser. Real provider connectivity, Turso transactions, email delivery, model availability, browser layout/accessibility and public-load capacity remain unverified. Managed preview could not start this Python project because it expects a JavaScript package manifest; no browser test is claimed.

## Official references checked 11 September 2026

- NVIDIA free hosted development/testing: https://developer.nvidia.com/nim
- NVIDIA API keys and examples: https://docs.api.nvidia.com/nim/docs/api-quickstart
- OpenRouter free router: https://openrouter.ai/openrouter/free
- Groq account/model limits: https://console.groq.com/docs/rate-limits
- Gemini free-tier eligibility, pricing and data handling: https://ai.google.dev/gemini-api/docs/pricing
- Render free limitations: https://render.com/docs/free
- Turso plans: https://turso.tech/pricing
- Turso HTTP protocol: https://docs.turso.tech/sdk/http/reference
- Brevo transactional API: https://developers.brevo.com/docs/send-a-transactional-email

Provider terms, regional access and model availability can change. Recheck account dashboards before enabling any integration.

## Owner reports and background monitoring

Sign in as a verified account whose email is configured in `ADMIN_EMAILS`, then open **Owner**. Download summary metrics, daily activity, account records and health history as CSV files that open in Excel/Google Sheets. A printable HTML report can be saved as PDF using the browser Print command. These are real database reports, not sample usage figures. No report is emailed automatically; no recipient has been configured.

Account exports include ID, email, display name, verification/suspension status, registration date and most recent retained account action. Password hashes and session/reset/verification tokens are excluded. Owner authorization is enforced by the server; exports are audited and formula-like CSV cells are neutralized. Keep downloaded account reports private. Each account/health export is capped at 5,000 rows; continue with `after=<last id>` for subsequent batches. The dashboard includes an account continuation control.

The background thread starts with `server.py`, checks core public feeds and database availability, and retries failed public reads with exponential backoff up to one hour. It does not retry account mutations, charge API credits for health probes, or rewrite source code. Sanitized recent exception codes are visible to the owner; source health snapshots are retained in the database for seven days. Error details intentionally exclude request text, URLs, keys and email addresses. The monitor cannot independently detect a dead server or repair code bugs. It runs only while the hosting process is awake and has not been configured as an external uptime service.

Additional official source documentation:
- https://docs.dexscreener.com/api/reference
- https://docs.gopluslabs.io/reference/api-overview
- https://docs.gopluslabs.io/reference/tokensecurityusingget_1
- https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/

New integrations are fixture-tested, not live-validated. A provider requiring authentication or denying a request remains unavailable; no paid subscription or credentials are obtained automatically.
