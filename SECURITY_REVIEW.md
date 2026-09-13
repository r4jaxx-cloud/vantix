# Security work — 2026-09-13

This branch is not a complete penetration-test certification. Do not equate a successful deployment with security validation.

## Implemented
- Cookie-only session authentication; production requests fail closed on missing/mismatched origin configuration.
- Argon2id new hashes (19 MiB, 2 iterations, one lane), at most two concurrent hash operations. Existing PBKDF2-600000 hashes remain verifiable and upgrade at successful login.
- Session issuance checks the authenticated password version inside the write transaction, preventing login from creating a session after a concurrent password reset.
- Reset token consuming DELETE includes expiry and uses RETURNING; two concurrent local requests yield one success. Replays do not change the password again. Logout removes the database session.
- Production registration/reset/resend use identical eligible-account responses with bounded background email jobs. Unknown logins perform dummy hash verification. Legacy-hash timing differences may remain until migration; do not claim mathematically constant-time HTTP responses.
- Persistent email-wide and email+peer throttles; no trust in arbitrary forwarded headers. Peer address may be the hosting proxy, so per-email control remains important. HMAC identifiers avoid raw IP storage in rate-limit buckets.
- No visitor IPs in public responses or owner exports. Application access logging remains disabled. Hosting/provider logs are separately controlled and not anonymized by this patch.
- Account security audit table records registration/email requests/login failures/login/logout/password reset, plus pre-existing moderation/export auditing. It excludes passwords, raw tokens and IPs and is retained for 30 days. This is not exhaustive infrastructure auditing.
- Literal SQL lookup maps for dynamic table choices; user values remain bound parameters.
- URL validation rejects non-HTTP(S), credentials, control characters, backslashes and invalid ports. Input validation rejects invalid Unicode/control sequences without altering passwords.
- Hardened XML parser for external feeds.
- CSP allows the hashed application script, TradingView script/frame origins and the two crypto WebSockets. Inline executable event attributes are removed and replaced by a literal-only command dispatcher. No eval. Inline styles remain allowed for existing layout.
- Generic server errors preserved; owner reporting authorization preserved.

## Checks
- 46 backend checks, 36 launch/security/operations tests and 35 simulated UI checks passed during local verification.
- SQLMap 1.10.9 ran against a loopback fixture, authenticated `/api/saved?kind=watchlist`, level 1/risk 1, Boolean/error/UNION techniques. It found no injectable parameter in that scope. Invalid payloads returned 400. This is not a scan of every endpoint or the deployed service.
- Requirements audit: no known vulnerabilities reported for the checked dependencies (rerun in CI).
- Static scan findings were reviewed: table names now use literal maps; remaining placeholder construction uses only '?' per validated numeric id; HTTPS outbound calls use fixed providers/validated URLs. Suppressed exception cleanup paths do not return exception details. Full static output is retained by GitHub CI.
- Real-browser CSP/navigation/XSS regression is included in CI. Local Chromium download failed, so no local browser pass is claimed.

## Gates before merging/deploying
1. GitHub regression and real-browser workflow must pass at the branch head. TradingView is mocked in browser regression; live chart/frame loading still needs a deployed smoke check.
2. Render Build Command must install dependencies: `pip install -r requirements.txt && python3 -m compileall -q .`. Updating render.yaml does not automatically reconfigure a manually created service. Keep Start Command `python3 server.py`. Do not merge code requiring these dependencies into an instance that only compiles files.
3. Verify real Turso transaction behavior, login with an existing account, reset email and live chart after staging/deployment. Secrets remain in Render.
4. Do not run public SQLMap load against real accounts or interpret this scoped result as complete absence of injection.

## Deliberate limits
Connection pooling is not introduced: mutable libSQL HTTP transaction batons cannot be safely shared across threads without a dedicated design and workload tests. Existing request cleanup/rollback is retained. Pooling is a performance consideration, not an automatic security fix.
Email jobs are bounded and in-memory; a host restart may interrupt delivery. Users can resend. No claim of durable email scheduling or always-on free hosting.
