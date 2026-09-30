# VIRTLINK — Codex continuation handoff

Prepared 30 September 2026 from this project chat only. This is a working handoff, not a verbatim chat transcript. Start by reading this file and inspecting the actual repository and connected services. Do not assume described work is live.

## User instructions

- Use only this chat/handoff and VIRTLINK project sources. Do not use memory from other chats or mix other projects into this work.
- Keep replies short and usage economical. Continue authorised work without repeatedly asking permission. No background-work promises unless a real scheduled job exists.
- Free services only; Render is the interim host. The user will obtain a domain later. No paid fallback, subscription or upgrade without explicit approval.
- Preserve the approved navy/electric-blue futuristic design. Modern professional social network, not a generic AI template. Optional World is a separate feature.
- Preserve VANTIX and its backup. Do not deploy VIRTLINK to VANTIX production or merge the VIRTLINK work into main.
- VIRTLINK has its OWN Supabase organisation and project. Never use Mingovo or another project's accounts/database.
- No visible AI features for now. Focus on accounts, networking, profiles, followers, groups, private messages, jobs, brokers/professionals, investors and proposals.
- Search must be typed directly in the existing bar; no second input/dropdown appearing underneath. Avoid duplicated navigation/banners. Search is not an AI question engine.
- Public users should eventually have one account across all features. Private messages must have genuine end-to-end encryption, with no admin decryption backdoor; HTTPS alone is not E2EE.
- Verified ticks require extended identity review and manual approval; investors require additional organisational and relevant regulatory checks. Email verification is not an identity or investor badge.
- Never promise an unhackable site or blanket legal immunity. Use multiple tested security layers.

## Repository and deployment

- GitHub: https://github.com/r4jaxx-cloud/vantix
- Continue from remote branch `feature/virtlink-accounts`.
- Draft PR #30: https://github.com/r4jaxx-cloud/vantix/pull/30
- PR target: `feature/virtlink-preview`, NOT `main`.
- On 30 September PR30 was open, draft, unmerged. Implementation head before this handoff: `271e6851f2b863242e6ab129c79f27c2dc3fa8fd`.
- Live preview: https://virtlink-preview.onrender.com
- Last confirmed live preview commit: `e52a145e7e73851798bbcc858105726f6a3895c6`. It does NOT contain the new account screens yet. Check current state before deployment.
- Render static service: `srv-datc0il9fdbs73b5a2v0`; workspace `tea-dahar51t0dsc73facie0`.
- Auto-deploy branch: `feature/virtlink-preview`; build `python virtlink/build.py`; output `virtlink/dist`; `SKIP_INSTALL_DEPS=true`.
- Do not trigger a second deploy when an auto-deploy is already running. Verify deployment reaches live and test the actual URL.
- VANTIX live site to preserve: https://vantix-60ui.onrender.com ; Render `srv-dailspm7bikc7396mkj0`.
- VANTIX backup branch: `backup/vantix-before-virtlink-2026-09-28` at `7c8082d6d7f183449b87f3ce26b57bf9b5555543`.

The old local workspace was `/workspace/scratch/00a47aca9d56/vantix`. Local branch `feature/virtlink-preview` includes commits `819c27a` and `a82d207`, while remote commits were written using the GitHub connector. Histories differ. Prefer a fresh checkout of the remote accounts branch; do not force-push or reset shared work. Shell pushes previously lacked credentials; the GitHub connector worked.

## Exact continuation point

The user agreed to private testing, with public signup closed and custom SMTP/domain setup deferred. They were asked to turn OFF **Allow new users to sign up** at:
https://supabase.com/dashboard/project/hnoqhdqnvvndyipcoudi/auth/providers

They have NOT yet confirmed that toggle is off. Verify `GET /auth/v1/settings` using the project's publishable key: `disable_signup` must be true. Existing tools can read databases but do not expose Auth configuration changes. If still enabled, guide the user through that setting. Do not assert invite-only operation merely because no signup form exists.

Next: finish review of PR30, verify invite-only configuration, then deploy the test account screen to the preview branch, create/provision an appropriate test account and test real login → MFA enrolment/challenge → profile save/reload → sign-out. Follow the user's explicit permission requirements for external email/invitations; never request a password or secret in chat. No actual browser login, valid CAPTCHA, email delivery or real MFA flow has yet passed an integration test. Current tests cover SQL policies, mocked service calls and the browser's missing-CAPTCHA gate.

## Separate Supabase infrastructure

- Project name: VIRTLINK
- Ref: `hnoqhdqnvvndyipcoudi`
- Organisation: `qhdcbtfeyscxmyizkvwt` — `VIRTLINK organisation`, Free plan.
- Region `eu-central-1`; last checked ACTIVE_HEALTHY, Postgres 17.
- Dashboard: https://supabase.com/dashboard/project/hnoqhdqnvvndyipcoudi
- API origin: https://hnoqhdqnvvndyipcoudi.supabase.co
- Fetch publishable keys from the connector if needed; the public key is also intentionally included in `virtlink/account-page.js`. Never put service-role, SMTP, Turnstile secret or database passwords in browser code or git.
- `list_organizations` sometimes returned only the other organisation; direct `get_project` and `get_organization` confirmed VIRTLINK, and SQL tools successfully operated on the explicit project ref. Do not confuse list visibility with lack of a project.

### Database work already APPLIED

Migrations (do not rerun blindly):
1. `20260929175320_virtlink_accounts.sql`
2. `20260929175539_require_verification_expiry.sql`

Both committed under `virtlink/supabase/migrations/`. Tables:
- `public.virtlink_profiles`: private owner-only profile read/insert/update, bounded fields, unique lowercase username, column grants prevent ownership reassignment. Even discoverable=true remains owner-only pending a reviewed directory publication policy.
- `public.virtlink_verifications`: owner can read but cannot insert/update/award approval. Approval requires reviewed_at and non-null expires_at after review. No evidence documents or reviewer interface.
- Helper `virtlink_private.account_ready()`: narrowly scoped security-definer function with empty search_path, restricted execute permission. Requires JWT aal2, current confirmed email, non-anonymous existing user and no active ban. No authorisation based on user_metadata.
- No message table or E2EE implementation.

Database regression SQL: `virtlink/backend/test_accounts.sql`. Fixtures use generated users inside a transaction and are rolled back. Passed own read/update, cross-user read/write denial, owner reassignment denial, self-verification denial, forged user_metadata, MFA/email/ban checks, anonymous denial, approval-expiry constraint. Zero accounts/profiles remained after these tests on 29 September. Security advisors returned no findings after both migrations. These results are not a full audit.

Known security work remaining: immediate session revocation checks for sensitive operations, full account recovery, reviewer role separation/audit, abuse/report/block flows, privacy deletion, retention/backups, real multi-user browser testing. Existing RLS relies on access-token lifetime plus current user/email/ban state.

## Turnstile and email setup

- The user created a Cloudflare Managed Turnstile widget for `virtlink-preview.onrender.com`.
- Public site key: `0x4AAAAAAFJYFDkwLT_FJO_L`.
- User entered the secret directly into Supabase; it was NOT shared in chat.
- Supabase protection settings: https://supabase.com/dashboard/project/hnoqhdqnvvndyipcoudi/auth/protection
- Live Auth endpoint tests returned HTTP400 `captcha_failed` for both invalid token and missing token. This proves rejection, not successful real-human completion.
- Last public Auth settings: email enabled, anonymous users disabled, mailer_autoconfirm false, disable_signup false (needs changing as above).
- User owns no domain yet and chose to defer it. Leave custom SMTP off for now. Default Supabase mail only delivers to project-team addresses and has very low limits; cannot support public signup. Do not remove email confirmation to work around this.
- Correct SMTP link: https://supabase.com/dashboard/project/hnoqhdqnvvndyipcoudi/auth/smtp . The previously suggested `/auth/emails` URL returned 404.

## New test account implementation — BUILT, NOT DEPLOYED

- `virtlink/accounts.html`, `accounts.css`: separate labelled test account page using existing visual styling. No registration form or social publishing.
- `virtlink/account-page.js`: live Supabase client; Turnstile sign-in, authenticator enrolment/challenge, private profile form, local-session sign-out. No secret values logged. No auth URL callback/invitation/password-setup flow (detectSessionInUrl=false), no password/MFA recovery yet.
- `virtlink/account-service.js`: injected SDK service, getUser and MFA guards, owner-filtered reads/updates, whitelisted fields, owner ID from verified user rather than input, blocks missing CAPTCHA before sending passwords.
- `virtlink/package.json` and lock: `@supabase/supabase-js` 2.117.2; `esbuild` 0.28.2. Do not remove version pins or lockfile.
- SDK is bundled locally. Session storage key `virtlink-test-auth-v1`; demo state remains separate. No service-role key. No shared account session with VANTIX or other projects.
- Account-page CSP allows only self, the exact VIRTLINK Supabase origin, and challenges.cloudflare.com; QR image is data image. Original preview CSP stays unchanged.
- `virtlink/build.py` now runs npm ci --ignore-scripts and npm run build:accounts, then copies accounts.html/css into dist. Render must have compatible Node/npm; confirm actual build.
- No link from main preview login to new accounts.html yet. Keep demo and actual account state clearly distinguished until their integration is implemented.
- Known limitation: production revocation/expiry races, multi-tab behaviour, recovery and real error states need review/integration tests. Do not treat the initial code as guaranteed secure.

### Validation

- `npm --prefix virtlink test`: eight account-service tests passed.
- `npm --prefix virtlink audit --omit=dev`: zero known vulnerabilities at test time.
- `python virtlink/build.py`: local build passed.
- GitHub Actions run `36612233498`, job `109556280729`: SUCCESS for head `271e6851f2b863242e6ab129c79f27c2dc3fa8fd`.
- Workflow `.github/workflows/virtlink-preview.yml`: build, service tests/audit, JS syntax, Playwright browser tests and screenshots. Branch filters include accounts branch.
- `virtlink/test_preview.py`: existing desktop/mobile preview flows plus accounts missing-CAPTCHA test. The account test mocks Turnstile script, blocks all Supabase requests, confirms no password request is sent without CAPTCHA, clears password, checks private panels hidden, no overflow/runtime errors.
- Browser tests therefore do NOT validate real login, CAPTCHA success, TOTP, email or multi-user sessions. Explicitly report this distinction.

## Existing live preview features

The social preview is vanilla JavaScript, no live user accounts yet:
- Welcome city hero, feed, profiles, follows, comments, saved items, network, jobs, communities, events, marketplace, messages, World concept, investors/proposals, draft policies.
- Hash routes and inline search; search result destinations still need refinement to exact job/investor/item.
- Demo actions persist in sessionStorage only, with sample labels. DMs are sample strings, NOT encrypted messages or delivered chats.
- Desktop sidebar pages hide duplicate top navigation; header search max-width 360px. Mobile More provides extra sections.
- World is artwork, not working 3D, live voice or avatars. Do not imply interactive controls painted into the image work.
- Four fictional investor examples, filters, private session-only proposal drafts and reviewed introduction drafts; no real submissions or verified investors.
- Policies in `virtlink/policies.js` are pre-launch drafts. Operator legal name/address/jurisdiction/support/privacy contacts not supplied. Do not invent these or borrow another project's company details.
- `virtlink/LAUNCH.md` describes broader blockers but predates the database/test-page work; read this handoff and backend README for current status.

## Design references from this chat

Approved references are `VIRTLINK_Concept_Deck.pptx` and `VIRTLINK Futuristic Networking Dashboard.png`, provided in this conversation. Original upload paths may not exist in a new environment. Current code and `virtlink/world.b64` preserve the implemented direction. Ask for reattachment if exact reference inspection is needed; do not silently substitute another project's designs. The user previously requested not reading these via Library.

Design: dark navy/electric blue, premium professional social network, city hero, left navigation, central feed and right rail; World optional. User insists keeping the approved visual direction.

## After test accounts

1. Integrate real profile/account state into the social UI, preserving separation from sample data.
2. Real feed/follows/groups with ownership and moderation; genuine reporting/blocking, notifications and messages.
3. Use a maintained reviewed E2EE protocol/SDK, not a homemade cipher. Matrix was researched as one candidate, not chosen or provisioned. Needs device verification, key recovery, multi-device behaviour, encrypted attachments and deployment/cost decisions.
4. Identity and investor verification process with restricted evidence, human review, expiry/revocation and accurate badge explanations. Provider and operator/legal readiness remain unresolved.
5. Private proposals with selected-recipient permissions and regulatory review before real investor introductions.
6. Domain, production email, operator policies, monitoring, backups/recovery/deletion, real security tests before public launch.

## Copyable starting instruction

Continue VIRTLINK from branch feature/virtlink-accounts in r4jaxx-cloud/vantix. Read VIRTLINK_CODEX_HANDOFF.md and inspect draft PR30. Keep the approved design, use only this project's context, preserve VANTIX, use only VIRTLINK Supabase hnoqhdqnvvndyipcoudi, and use free services. First verify that public signup has been disabled, review the test-account code and test results, then complete a safe test deployment and real-account verification. Do not claim messaging is encrypted: E2EE is still unimplemented. Keep updates short and be exact about what is built, deployed and tested.
