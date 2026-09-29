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

The public Render site remains the labelled preview; no signup or messaging claim has been changed.

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
