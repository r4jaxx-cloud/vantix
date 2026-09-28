# VIRTLINK launch status — 28 September 2026

## Released
- Separate Render static preview, separate Git branch; VANTIX production preserved.
- Approved navy/blue layout, welcome, social feed, network, jobs, messages, groups, events, marketplace, World visual concept.
- Investor discovery, business-proposal drafts and explicit introduction review.
- Draft terms, privacy, community and investor-verification policies; no approved investor badges.
- No live signup, uploads, investor contact or payments; sample data is labelled.
- Self-hosted assets; restrictive script/connect/content policies; user content escaped; session-only preview state.

## Blockers — do not enable public registration or investor introductions yet
1. Confirm operator legal name, address, support/privacy contact, operating jurisdiction and target countries. Obtain review of final terms, privacy notice and regulatory scope of introductions/proposal sharing.
2. Provision separate account/database infrastructure. The connected Supabase account returned no projects on this review; no VANTIX credentials or data have been reused.
3. Configure email delivery, verification, server-side bot checks, MFA and recovery; test account enumeration, brute force, session rotation/revocation, CSRF, IDOR and abuse handling.
4. Choose and configure identity/liveness and organisational-evidence workflow. Keep identity evidence out of normal chat and public profile storage. Establish lawful basis, retention, restricted staff access and review/appeals.
5. Implement investor approval from trusted server records with human review, independent firm-contact checks, relevant regulatory checks, expiry, suspension and revocation. No self-approval and no badge based solely on profession or email.
6. Implement private proposal ownership and selected-recipient authorisation; tests must prove other users and unapproved/suspended investors cannot access it. Scope financial-promotion permissions before distribution.
7. Implement maintained, reviewed end-to-end messaging with verified device keys, recovery and multi-device handling. Do not invent a custom crypto protocol or label HTTPS alone E2EE.
8. Connect real reporting, blocking, moderation, appeals, incident response, backups and restore tests; provide privacy rights and account deletion workflows.
9. Run dependency/security review and multi-user end-to-end tests on an isolated staging environment; resolve findings before a limited beta.

World remains an illustration, not a live 3D environment. Do not promise avatar movement, live voice or proximity chat in this release.
