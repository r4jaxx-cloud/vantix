# VIRTLINK concept preview

Phase 1 from the user's VIRTLINK_Concept_Deck.pptx. This isolated frontend preserves the approved navy/electric-blue visual language and uses the supplied Global Hub concept artwork on the separate World page.

Run `python virtlink/build.py`, then serve `virtlink/dist` with any static server. Render: build command `python virtlink/build.py`; publish path `virtlink/dist`.

## Scope

Clickable welcome, feed, network search, profile editor, opportunities, communities, event preferences, marketplace, sample messaging and World concept. Examples are labelled throughout. All mutations remain in sessionStorage. No users, jobs, bookings or messages are represented as live. Signup and login are deliberately closed; no credentials are collected. This is not the production social platform or a live 3D environment.

VANTIX production remains on the existing main branch. Do not merge this preview branch into main or connect its deployment to VANTIX's production database.

## Required production security gate

- Server-side validated bot challenge, email verification, two-factor authentication and recovery.
- Reviewed password hashing, session lifecycle, authorization and abuse controls.
- Maintained, reviewed end-to-end messaging implementation with device verification and encrypted recovery. No home-grown cryptographic protocol.
- Independent review and tests for account takeover, access-control bypass, injection, stored XSS, session/CSRF protections, abuse, deletion and recovery.
- Minimize collected profile details; do not request identity documents until a secure verification provider and retention policy are established.

HTTPS protects transport. It is not end-to-end messaging encryption. No identity or E2EE claims may be made until the corresponding implementation is configured and verified.
