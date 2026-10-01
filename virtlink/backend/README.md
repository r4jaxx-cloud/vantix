# VIRTLINK account foundation

Target: `hnoqhdqnvvndyipcoudi`, organisation `qhdcbtfeyscxmyizkvwt`
(`VIRTLINK organisation`, Free). No other project's database or users are used.

Applied 29 September 2026:
- Private onboarding profiles with ownership policies and restricted column grants.
- Database access requires confirmed email, a non-anonymous, non-banned account and an MFA (`aal2`) session.
- Separate verification records, read-only to their owner. No client can award an identity, professional or investor badge.
- Reviewed approval requires a review date and expiry. Applications must check expiry and revocation when displaying a badge.
- No credentials, identity documents or chat plaintext are stored in these tables.

`test_accounts.sql` creates temporary fictional users inside a transaction and rolls everything back. Tests cover own-profile read/update, cross-user read/write denial, ownership reassignment, self-verification denial, user-metadata forgery, MFA enforcement, email confirmation, banned accounts, anonymous access and approval expiry. Passed on the target database; no fixtures remain. Supabase security advisor returned no findings after the first migration. This is a database-policy test, not a complete security audit.

## Remaining work before enabling accounts

The public Render site remains the labelled preview. A separate `accounts.html` provides test-only sign-in, Turnstile, TOTP enrolment/challenge, sign-out and private profile saving. It does not publish profiles to the sample social feed. No signup form, invitation/password setup, recovery or E2EE messaging is implemented. The SDK is pinned and locally bundled, with session-scoped auth storage. Eight service tests pass; these are not a substitute for real-account browser testing.

The public Turnstile site key is configured. On 29 September the Auth endpoint rejected both missing and deliberately invalid CAPTCHA tokens. Email auto-confirm and anonymous auth were disabled. **The Auth API still reported `disable_signup: false`**: the site has no registration form, but the owner must disable new-user signup in Supabase before calling the service invite-only. The connected tools do not expose that setting.

1. Configure dedicated transactional email and confirmed-email signup; test actual delivery and recovery. Never send a secret SMTP credential through chat or commit it.
2. Create a Cloudflare Turnstile widget for `virtlink-preview.onrender.com`. Configure its secret in Supabase Authentication > Bot and Abuse Protection. Supply only its public site key to the frontend. Server rejection of missing/invalid tokens must be tested.
3. Configure exact redirect URLs, password policy, auth rate limits, session expiry and account recovery. The connector used here does not expose Auth configuration mutations.
4. Integrate pinned Supabase SDK, login/signup/recovery, MFA enrolment/challenge/recovery, sign-out, user-scoped state cleanup and saved profiles. These flows are NOT implemented by the SQL migration alone.
5. Test independent browser sessions with two actual staging accounts. Database tests simulate JWT claims; they do not test token issuance, email delivery or the MFA UI.
6. Implement immediate session-revocation enforcement for sensitive actions; current row policies rely on verified access-token lifetime, plus current user existence/ban/email state.
7. Finalise operator identity, privacy/terms and security/abuse operations before public registration.

Discovery remains private by default, including rows marked discoverable, until publication, block controls and directory policies are implemented. No verification reviewer interface, identity provider, E2EE system or public verification badges are enabled. Those are subsequent work, not guarantees supplied by Supabase.

## Reproduction

Apply committed migrations in order to an empty, isolated Supabase project. The remote migration service assigns its own timestamp; filenames should match its recorded versions. Execute the test SQL as database owner, then run Supabase security advisors. Never run these against VANTIX or another project.


## September 30 account flow update
- Saving opens a read-only view of the real saved profile; Edit profile returns to the form.
- Authenticator enrollment is optional for ordinary profiles. If a verified factor exists, aal2 is still required by the database and client. Verification records retain mandatory aal2.
- Initial email confirmation remains required. New-device email challenges/trusted-device records are requested but NOT implemented or enabled. Custom email delivery and a server-enforced device challenge are launch blockers. Never describe existing sessions as device verification.
- Security advisor reports leaked-password protection disabled: https://supabase.com/docs/guides/auth/password-security#password-strength-and-leaked-password-protection . Remains a launch review item.

Main website now loads the current saved profile through the same session and owner-only service. Login opens accounts.html; Edit profile opens the saved editor; Sign out revokes the local session and removes account identity from the main page. Real profile details are not copied into preview session storage. Feed posts, follows and messages remain session-only demos.


## Member feed (private testing)
Signed-in users with saved profiles can publish text posts, read the latest 50 member posts and delete their own. Server trigger copies author name/username from the private profile; clients cannot supply those fields. No anonymous feed access. Other profile fields stay owner-only. Posts are persistent; follows/comments/messages remain previews. Refresh loads new posts; no automatic realtime subscription yet. Author names are publication-time snapshots.
The insert guard limits remaining posts to 5/minute and 50/day; deleting posts releases that count. This is a basic test-stage guard, not a durable anti-spam ledger. Public signup remains closed until moderation/report/block workflows and launch requirements are complete.
Validation: backend/test_feed.sql uses rollback-only accounts to check member reads, author spoof prevention, column permissions, owner-only deletion, MFA, private profile isolation, anonymous denial and the posting guard. Browser tests cover composer events, text escaping, deletion confirmation and sign-out clearing. Real multi-user sign-in tests are still outstanding.

## Saved reactions
Member likes and comments are persistent. Each user has at most one like per post and can remove their own likes/comments. The feed RPC uses SECURITY INVOKER with RLS, and returns counts plus the caller's liked state. Comment author identity is supplied by a server trigger. Comment reads show the latest 100 in chronological order. No realtime subscription, threaded replies or public moderation workflow yet. Database regression tests: test_reactions.sql.

Account setup now includes a required photo for first-time UI onboarding and optional authenticator enrollment. Photos are cropped/re-encoded in-browser to 256px JPEG (up to 100KB) and stored in the owner-only profile row; original uploads are not retained. Existing profiles may keep initials. Saving navigates to the main profile, after optional authenticator setup if chosen. Public registration remains closed; the Create an account panel explains invite-only testing. Email delivery/recovery/new-device checks remain outstanding.
