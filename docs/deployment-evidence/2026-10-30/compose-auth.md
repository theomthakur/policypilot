# Compose + Keycloak: real sign-in, two users (2026-10-30)

Stack: `docker compose -f docker-compose.yml -f docker-compose.auth.yml up -d --build`, Keycloak 26.0 (dev mode), passwords generated at start and not stored here. Driven by `scripts/e2e/flow.mjs` in headless Chromium.

```
[alice] sign-in screen shown to a signed-out visitor
[alice] signed in through the identity provider
[alice] uploaded alice-private.pdf
[alice] documents visible: 15; not from the shared corpus: 1. Alice private note
(signed out, then in again in a fresh browser)
[alice] documents visible: 15; not from the shared corpus: 1. Alice private note     <- conversation resumed
[bob]   sign-in screen shown to a signed-out visitor
[bob]   signed in through the identity provider
[bob]   documents visible: 14; not from the shared corpus: none                      <- isolated
```

Screenshots: `compose-alice.png`, `compose-bob.png`.

A bug found by this run and fixed: after signing in again the document list was fetched before the conversation was re-attached, so Alice briefly lost sight of her own upload. The list is now refreshed whenever the conversation changes (commit following this file).
