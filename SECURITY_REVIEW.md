# Security checklist triage — 2026-09-13

This is a code review of the supplied checklist, not a penetration test or a claim that all items are fixed. The original scanner output, file/line references and exploit examples were not supplied. Findings must be traced to reachable code.

| Item | Current evidence and disposition |
|---|---|
| 1. SQL injection / table whitelist | Reviewed dynamic table identifiers in server.py and launch_features.py are fixed tuples or ternaries after kind validation. User values are bound parameters. No injectable table identifier confirmed in these paths. Obtain original finding location before concluding repository-wide safety. |
| 2. Bearer bypass | Production previously ignored Bearer headers, but non-production accepted valid session tokens from Authorization. It did not skip session lookup. This branch removes that alternate path entirely. Existing legacy backend tests need updating to cookies. |
| 3. Argon2 | Current hashes are salted PBKDF2-HMAC-SHA256, 600000 iterations, not plaintext or a fast unsalted hash. Argon2id migration is pending: add tested dependency, bound hashing concurrency/memory, retain legacy verification and rehash after successful authentication. Render build currently only compiles Python; blindly adding an import would break deployment. |
| 4. CSRF | Confirmed production misconfiguration gap: absent configured URL could fall back to request Host when an Origin was present. This branch fails closed when production URL or Origin is missing or mismatched. Startup preflight already requires URL. Local development behavior remains separate. |
| 5. HTML escaping | Current frontend uses esc for dynamic text, and source-link helpers. Escaping must be reviewed by output context, not applied indiscriminately to stored input. No specific unescaped sink supplied. Full browser XSS coverage pending. |
| 6. URL validation | HTTP(S) scheme and authority checks exist, but credential/control-character/port validation needs tightening in server and browser paths. Provider outbound URLs are fixed. Pending. |
| 7. Enumeration | Registration exposes existing accounts with 409; login skips password hashing for unknown accounts. Reset/resend messages are generic in production, but timing depends on email sending. Confirmed hardening work remains, including a uniform response and bounded email dispatch approach. |
| 8. Reset race | Reset already uses DELETE RETURNING and checks deletion result before updating the password in the write transaction. Sequential single-use is tested. Add concurrent local and libSQL tests and include expiry in the consuming DELETE; transaction-expiry cases still need review. |
| 9. Logout revocation | Already deletes the hashed session token from the DB and clears the cookie. Existing integration checks confirm revocation locally. |
| 10. Rate limiting | Auth currently has an in-memory per-socket-IP limiter. No per-email limiter. Shared proxies/process restarts and a bounded persistent email+IP strategy need attention. Do not trust arbitrary X-Forwarded-For without a verified proxy contract. |
| 11. Audit | Moderation and export audit rows exist; login/action events exist. Security event coverage for failed logins, password reset and logout is incomplete. Never record passwords or raw tokens. |
| 12. CSP | Absent. The page has inline script, onclick handlers/styles, exchange WebSockets and TradingView scripts/frames. A strict policy requires corresponding frontend refactoring and browser verification. A broad unsafe-inline policy is not a complete XSS fix. |
| 13. Unicode | Length checks exist but field-specific Unicode handling needs review. Normalize display text as appropriate; do not silently normalize existing passwords or change account identity matching. Reject problematic controls while retaining legitimate languages. |
| 14. Error verbosity | General request failures already return a generic 503; detailed exception classes are recorded internally. Some explicit validation messages are returned. No raw database exception exposure confirmed in reviewed HTTP wrapper. |
| 15. Pooling | Connections are request-tracked and closed; remote libSQL uses a stateful HTTP baton and transactions. Pooling is a performance/design consideration, not by itself an injection vulnerability. Benchmark and test transaction isolation/rollback before pooling; never share one mutable connection across request threads. |

## Validation of this branch
17 existing launch/provider tests pass with cookies, including reset, authorization, moderation and exports. Three additional manual assertions pass: Bearer rejected, cookie parsed, production missing public URL rejected even with matching attacker-controlled Origin/Host. These are local tests, not live Render validation.

## Deployment status
Draft security review branch only. Not merged or deployed. Resolve the remaining items and test migration/browser compatibility before treating the checklist as complete. Keep secrets in hosting configuration. This document may become outdated: check the latest commit and update statuses as work progresses.
