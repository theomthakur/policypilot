# 0009. OpenID Connect sign-in, server-side sessions and per-user ownership

**Status:** Accepted, 2026-10-30. Refines [0008](0008-single-vm-compose-deployment.md): the demo passcode stays an operational cost gate, but it is no longer the only identity.

## Context
Until now a conversation was a UUID cookie behind a shared passcode. That protects spend, not people: nothing says who owns a conversation or an upload. A university deployment needs real sign-in and a clear ownership rule.

## Decision
- **Protocol:** OpenID Connect Authorization Code with PKCE, `state` and `nonce`, through Authlib and joserfc. ID tokens are accepted only with an asymmetric algorithm, a matching issuer and audience, an expiry and the nonce this browser started. Provider tokens stay on the server.
- **Session:** after sign-in the server issues its own opaque, random cookie (`pp_auth`, HttpOnly, SameSite=Lax, Secure behind TLS). Only its SHA-256 is stored, with an expiry and a revocation time, so logout and expiry are enforced server-side, including for open event streams.
- **Identity:** a `User` is the immutable `(issuer, subject)` pair; email and name are display data and never grant anything.
- **Ownership:** each conversation row has `owner_user_id`. The `pp_session` cookie only *names* a conversation; it counts only when the signed-in user owns it. Uploads belong to the uploading conversation, so they inherit the owner. Shared corpus documents are readable by any signed-in user. Rows created before sign-in existed stay unowned and are never handed to the next person to sign in.
- **CSRF:** a request that changes state and carries the sign-in cookie must come from this site (`Origin` / `Sec-Fetch-Site`).
- **Fail closed:** `APP_ENV=production` refuses to start unless `AUTH_MODE=oidc` with an issuer, a client id and a signing key. `AUTH_MODE=test` (a built-in fake provider used by automated tests) is refused in production. `AUTH_MODE=off` keeps the passcode-only Compose demo working.
- **Provider:** Keycloak provides a reproducible local identity provider (`docker-compose.auth.yml`, the kind overlay). University single sign-on is a configuration change (issuer and client id), not code, but it has **not** been tried against a university provider.

## Alternatives considered
- **Passwords in the application:** more code, more risk, no single sign-on. Rejected.
- **JWT sessions in the browser:** cannot be revoked and would put provider tokens in the browser. Rejected.
- **A reverse-proxy auth layer (oauth2-proxy):** valid, but the ownership rule still belongs in the application and the proxy is one more moving part.

## Consequences
- Every protected route answers 401 `AUTH_REQUIRED` when signed out; the UI shows a sign-in screen and, after signing in again, resumes the person's latest conversation.
- Logging out of PolicyPilot does not end the identity provider's own session (single logout is not implemented).
- Evaluation against an authenticated deployment needs a provisioned test user; there is no bypass.
