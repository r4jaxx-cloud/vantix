# VIRTLINK launch roadmap

Updated: 1 October 2026. Current stage: private member testing.

VIRTLINK welcomes ordinary people, students, jobseekers and professionals. Stronger checks apply to sensitive roles and actions. VANTIX stays separate.

## How we tick off work

- [x] means the stated implementation/check is complete, not that the whole product is launch-ready.
- [ ] means unfinished or awaiting real-world verification.
- Each completed feature needs evidence: test result, deployment commit and date.
- Mock browser tests and rollback SQL tests do not prove real email delivery, CAPTCHA or multi-user operation.
- Update this file after each completed batch. No false live, verified or encrypted claims.

## Current checkpoint

Working on: critical account/session isolation. A delayed profile-save response could restore private UI data after sign-out; added session-revision guards and tests for sign-out/account changes during requests. No cosmetic work is prioritized.

Next: account recovery/email delivery (blocked by sender configuration), then server-enforced reporting/blocking/moderation. Real two-account acceptance checks remain open. Public signup remains disabled.

Known security setting: leaked-password protection disabled in Supabase; remains unresolved. No claim of a complete security audit.

## 1. Accounts and profile — first priority

- [x] Sign-in UI, field validation and human-check integration implemented.
- [x] Saved profile fields and owner-only database access implemented.
- [x] Profile editor opens on the same page; automated opening test passed.
- [x] Circular photo preview, replacement and image size/type handling implemented.
- [x] Successful sign-in routes to profile; profile save routes to profile.
- [x] Authenticator is optional; enrolled accounts require its code.
- [x] Database rejects revoked/expired session records; rollback SQL checks passed.
- [ ] Check actual sign-in redirect with and without enabled MFA on deployed site.
- [ ] Check photo/detail save, reload persistence, Cancel and username conflicts with real accounts.
- [ ] Complete safe signup, verified-email and password-recovery flows.
- [ ] Configure email sender/domain and verify delivery with real mailboxes.
- [ ] Implement and test the requested new-device email security check.
- [ ] Add session/device management and accessible MFA recovery/disable flow.
- [ ] Verify enabled leaked-password protection or document an effective alternative.

Acceptance: two real test accounts can complete onboarding, sign in, edit/reload their own profiles and recover access; neither can access the other account's private details.

## 2. Member feed

- [x] Database-backed posts, own-post deletion, likes and comments implemented.
- [x] Ownership, confirmed-account and session checks implemented.
- [x] Escaped member text rendering and automated regression checks added.
- [x] Sample profiles/messages/investors hidden from real member area.
- [ ] Test two real accounts posting, liking, commenting and deleting own content.
- [ ] Add reliable loading, retry and stale-session handling across all member actions.
- [ ] Implement stronger spam limits that cannot be reset by deleting content.
- [ ] Verify refresh/live-update behavior and label it accurately.

Acceptance: real activity persists after reload; sample content never mixes with member records; unauthorized edits fail.

## 3. Safety and moderation — before public access

- [ ] Report posts, comments and users; store reports privately.
- [ ] Block/unblock and mute, enforced in server/database access where relevant.
- [ ] Moderator queue, reviewed roles and restricted admin actions.
- [ ] Suspension, content removal, escalation and appeal workflow.
- [ ] Audit moderator actions and protect the audit record.
- [ ] Test abuse limits, repeated reports and blocked-user interactions.

Acceptance: a report reaches an authorized reviewer; ordinary users cannot view private reports or grant themselves moderator powers.

## 4. Networking and discovery

- [ ] Consent-based member directory and profile visibility settings.
- [ ] Search by name/skills with role, industry and region filters.
- [ ] Real follow/connect requests, acceptance and removal.
- [ ] Working notifications and clear notification preferences.
- [ ] Professional groups and group membership/privacy controls.
- [ ] Opportunities/jobs sharing with ownership and moderation checks.

Acceptance: search returns real permitted profiles; private fields remain private; connections and preferences persist.

## 5. Private messaging — gated until ready

- [ ] Select a maintained, reviewed E2EE solution; no custom protocol.
- [ ] Implement device keys, multi-device behavior and recovery.
- [ ] Permission-based conversations, blocking and user-controlled reporting.
- [ ] Review metadata exposure, retention and encryption claims.
- [ ] Independent review and real multi-device messaging tests.

Acceptance: prove the server cannot read message content; demonstrate recovery and blocked-user behavior. Keep real DMs disabled until this gate passes.

## 6. Verification and investors — gated until ready

- [ ] Define separate email, profile, organization and investor badge criteria.
- [ ] Human review, reviewer permissions, evidence minimization and audit trail.
- [ ] Badge expiry, revocation and suspension behavior.
- [ ] Secure verification provider/retention policy before collecting identity documents.
- [ ] Consent-scoped proposals and approval-based introductions.
- [ ] Validate applicable investor-introduction requirements for intended countries.

Acceptance: users cannot award their own badges; expired/revoked status loses relevant capabilities; proposals are accessible only to authorized recipients.

## 7. Privacy, legal and account lifecycle

- [ ] Supply operator name, jurisdiction, support and privacy contacts, target countries.
- [ ] Finalize accurate terms, privacy, community and moderation policies.
- [ ] Specify data purposes, retention periods and verification evidence handling.
- [ ] Implement account deletion, data export and documented retention exceptions.
- [ ] Establish support, complaints and incident-response procedures.

Acceptance: published policies match actual behavior; deletion/export and support requests work. Do not invent operator details or promise exemption from all responsibility.

## 8. Release engineering and security

- [ ] Review every user-content render path for stored/reflected XSS.
- [ ] Cross-account and role-permission tests for every real feature.
- [ ] Review dependencies, database policies, secrets and deployment headers.
- [ ] Separate staging/production configuration; protect release branch and deployment gates.
- [ ] Monitoring, alerting, log retention and realistic free-tier capacity checks.
- [ ] Backups plus successful restore test; rollback procedure.
- [ ] Desktop/mobile accessibility and full real-user journeys.
- [ ] Independent security review and resolution of material findings.

Acceptance: no known critical/high unresolved security issue; tested restore/rollback; passing deployment checks and real smoke tests.

## 9. Launch decision

- [ ] Choose the features actually included in the first release.
- [ ] Complete all relevant acceptance checks above; gated features remain unavailable.
- [ ] Run small controlled beta with ordinary users and resolve reported defects.
- [ ] Record release version, test evidence, remaining limitations and responsible operator approval.
- [ ] Enable public registration only after signup, moderation, recovery and privacy gates pass.
- [ ] Monitor initial release and retain a working rollback option.

Do not launch every unfinished feature together. A limited release can include working profiles/feed/discovery once their gates pass; messaging and investor workflows require their own gates.

## Verification record

| Date | Work | Evidence | Scope |
|---|---|---|---|
| 1 Oct 2026 | Direct profile editor | CI 36931930528 passed; Render deployment live | Mock browser UI/regression checks; not a full real-account save test |
| 1 Oct 2026 | Circular photo edit control | Commit ec9ef90ff2448adfec381cb794a5f6d84bcab874; CI passed; Render live | Preview/control regression; real photo persistence still needs acceptance check |
| 1 Oct 2026 | Active-session database checks | Applied migration 20261001134344; account/reaction rollback SQL tests passed | Simulated ownership/MFA/revocation checks |
