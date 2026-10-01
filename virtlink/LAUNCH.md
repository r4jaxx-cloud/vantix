# VIRTLINK readiness — 1 October 2026

## Product direction
Professional networking for everyone interested in work, business or learning, including beginners and students. Restricted test access is temporary, not permanent exclusivity. Investor and identity verification require separate evidence and human review; email confirmation and MFA are not identity badges.

## Working in the private member test
- Isolated Supabase project and Render static deployment; VANTIX production preserved.
- Existing-account login with Turnstile; confirmed email required. Optional authenticator enrollment; enabled factors must be challenged.
- Owner-only saved profiles and compressed profile photos; profile editing and main-page integration.
- Persistent member posts, likes and comments with author identity supplied by the server and owner deletion.
- Member routes hide fictional people, sample messages, investor tools and local demo actions. Visitors can still explore the clearly labelled demonstration.
- All member data policies check a matching, unexpired Auth session record, current user/email/ban status and applicable MFA requirement.
- SQL ownership/revocation tests and mocked browser CI checks. These are not a penetration-test certification or complete real multi-user validation.

## Release gates still open — no public registration or investor introductions
1. Configure and test email delivery, password recovery, optional MFA recovery and requested new-device email challenges.
2. Implement reports, block/unblock, moderator permissions, moderation queue, audit trail and appeals; test with separate real accounts.
3. Implement real directory discovery with explicit profile-publication consent and limits on disclosed fields. No automatic exposure of private profile records.
4. Choose a maintained E2EE messaging stack and test keys, recovery and multiple devices. Real DMs remain unavailable; World remains concept art.
5. Verification reviewer roles, evidence handling, expiry/revocation and approved investor introductions/proposal permissions remain unimplemented. No identity documents are collected yet.
6. User must supply operator legal name, address, jurisdiction, target countries and support/privacy contacts. Finalize reviewed terms, privacy/retention, account deletion and incident-response processes.
7. Establish staging/prod release controls, branch protections, backup/restore checks, monitoring and independent security review. Test real CAPTCHA/login/TOTP and multi-user flows.
8. Supabase advisor flags leaked-password protection as disabled. Review before launch: https://supabase.com/docs/guides/auth/password-security#password-strength-and-leaked-password-protection

Never merge VIRTLINK changes into VANTIX main as a release shortcut. Keep public signup disabled until the release gates are met.
