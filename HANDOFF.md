# VANTIX handoff

## 2026-09-19 follow-up
- Live public scan: GMGN trending/fresh returned rows for SOL, BSC, Base and ETH; Binance stream updated; FX reference rates and news loaded. Bybit had no stream quotes in this environment. Signed-in AI/accounts, persistence, load and mobile are not verified.
- This change preserves tiny token-price precision, refreshes GMGN filters automatically, rejects late responses from previous selections, labels stale/failed requests per section, and explains absent provider fields. Ratio displays no longer suggest positive price movement.
- GMGN field mappings match current official trenches documentation; missing fields remain unknown, with no speculative substitutions.
- Bybit parser matches the official spot snapshot example. Live connection timed out in the diagnostic environment; the root cause remains unresolved. Added connection/subscription status without changing endpoints or bypassing provider controls.
- Regression results are recorded in the pull request. Deployment and live verification remain separate from fixture checks.
- Remaining priorities: Bybit availability diagnosis, signed-in AI verification, licensed stock/commodity quote sources, account regression, production persistence and final launch checks.

Updated 2026-09-13. Status reflects work and user screenshots from September 12, not a new live audit.

## Goal and constraints
Build a public world and market information website using free services within their quotas and permitted use. Preserve the current dark blue design and side navigation. The user wants functional accounts, community discussion, accurate data labels, AI, owner reports and monitoring. Paid AI credits are a future idea, not implemented. Never promise unlimited free hosting, complete coverage or automatic error repair.

## Repository and deployment
- Repository: https://github.com/r4jaxx-cloud/vantix ; branch main.
- Website: https://vantix-60ui.onrender.com
- Render Python web service; root directory blank; build command `python3 -m compileall -q .`; start command `python3 server.py`.
- Standard-library Python backend and single index.html frontend, not an npm/Sites project.
- Turso/libSQL persistent database and Brevo email configured by the owner.
- Secrets stay in Render environment variables. Never commit keys, tokens, database files or account exports. Do not ask the owner to paste secrets into chat.
- Environment names include HOST, VANTIX_ENV, VANTIX_PUBLIC_URL, ADMIN_EMAILS, SUPPORT_EMAIL, SEC_USER_AGENT, LIBSQL_URL, LIBSQL_AUTH_TOKEN, BREVO_API_KEY, MAIL_FROM, FREE_ACCOUNTS_CONFIRMED. Consult current code and .env.example for requirements; do not overwrite existing settings blindly.

## Confirmed progress
- User confirmed email receipt, password reset and successful sign-in. Owner page visible in screenshots.
- Both Binance and Bybit browser streams showed LIVE quotes on Crypto exchange comparison in user screenshot.
- Binance server snapshot, ECB reference FX, Federal Reserve releases and USGS reports returned data in screenshots.
- Latest code update: free_data.py commit 840d7ccde3fd2c2072267ed65765c536c54697eb, index.html commit 2206f6b47ba37bd99c3635675c2568de40a033e1. Both contents read back and verified after push.
- 18 local data tests and 15 stream-state tests passed immediately before push. Earlier prepared build reported 140 local checks total; not all tests/documentation updates were pushed with these two files. Do not present that as live browser, load or production validation.

## Crypto behavior
Seven tracked USDT assets: BTC, ETH, BNB, SOL, DOGE, XRP, ADA. Main quote prefers fresh Binance, then Bybit. Comparison keeps exchange quotes separate; no averaging. Browser streams use source timestamps, stale detection and reconnect. Server REST snapshots are independently cached. Browser LIVE and server SNAPSHOT statuses describe different connections. AI and server alerts use snapshots, not browser ticks.

## Remaining work, in priority order
1. AI banner still says not connected. Inspect ai_service.py and provider configuration. Verify current free-tier eligibility, limits and public production terms before selecting providers. Configure keys privately in Render; test a real signed-in request, citations, limits and provider failure. Plugin connections in ChatGPT do not supply runtime AI or API keys to the website.
2. Bybit server REST feed and US EIA were UNAVAILABLE; GDELT also previously unavailable. Obtain sanitized error_code diagnostics from the actual deployment before changing endpoints. Bybit browser streaming already worked, so do not confuse this with REST availability or bypass provider restrictions.
3. Verify production account lifecycle, logout, verification/reset single use, permissions, saved assets, feed posting/moderation, alerts and owner exports. Registration success does not prove all flows. Keep user data private and test owner-only exports/authorization.
4. Review snapshot freshness through aggregation: market() currently rewrites retrieved_at using aggregate time; assess per-row stale filtering for AI and alerts. Confirm that stale rows are not presented as fresh evidence. Portfolio values may only refresh on render/load; do not assume every UI panel is live.
5. Owner reporting code exists (owner_reports.py, CSV/HTML exports), but automatic Google Drive reports are not connected. Validate actual counts and exports before scheduling or extending reporting. Never export password hashes, sessions or secrets.
6. operations.py has in-process monitoring/retries while the host is awake. It does not automatically repair source code and cannot ensure uptime when free Render sleeps. External monitoring and Cloudflare analytics were discussed, not configured.
7. Broader stock/commodity/news coverage is incomplete. Check free API quotas and public redistribution rights before integration. CoinGecko plugin was connected and a read succeeded in chat, but CoinGecko website API integration is not implemented. Google Drive, GitHub, Binance and Alpaca were also reported installed/connected in chat; verify access in the new assistant environment.
8. Run a focused public launch review and browser/mobile checks after changes. No complete production load test or all-feature launch sign-off has been done.

## Working instructions for the next assistant
Read current repository files and any applicable instructions first; compare against this dated handoff. Preserve changes made since this handoff. Do not rebuild the site or migrate hosting without a user request. Prefer small, reviewable commits with targeted tests. Verify deployed behavior separately from a successful GitHub push. Render may auto-deploy main; a documentation commit may also trigger a deployment. Update this handoff with changes, checks and remaining blockers. Coordinate assistants to avoid concurrent conflicting edits. Claude takeover is manual: the user opens Claude and provides repository access; there is no automatic transfer when chat usage ends.
