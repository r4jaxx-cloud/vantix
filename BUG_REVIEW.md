# VANTIX validation status

Implemented and checked locally: hashed cookie sessions; cross-origin write rejection; one-time reset tokens; per-account saved-item isolation; finite-value validation; idempotent reactions; moderation authorization; hidden-post comment rejection; threshold-notification deduplication; free-AI fallback and unknown-citation rejection; source freshness filtering; remote database protocol fixtures; nonblocking source refresh; request/thread limits; production configuration guard.

Passing suites: backend 46, data fixtures 11, launch/provider 17, operations/report/source tests 9, interface logic 35. Total 118.

Unresolved launch gates: real provider credentials and connectivity, verified email sender, live remote database transactions/restart persistence, browser visual and interaction testing, production infrastructure/load testing, and an operator responsible for reports/account requests. There is no deployed site or measured visitor-capacity result.

Known scope limits: token-security checks return provider flags when available and remain UNKNOWN on failure; no licensed equity price feed, complete breaking-news coverage, private messaging or background alert notifications. Free AI requests are heavily capped. Render free is suitable for a pilot and explicitly not recommended by Render for production.

New verified behavior: owner-only account and usage exports, CSV formula neutralization, export pagination, sanitized diagnostic events, monitor retry/backoff/recovery, missing security flags remain unknown, DEX quote timestamps are not invented, and GDELT indexing times are not mislabelled publication times.
