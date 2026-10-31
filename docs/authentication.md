# Authentication and ownership

Design and reasons: [ADR 0009](adr/0009-oidc-sign-in-and-ownership.md). This page is how to run it, how it behaves and how it was checked.

## Modes

| `AUTH_MODE` | Use | Notes |
|---|---|---|
| `off` | The default Docker Compose demo | Only the shared demo passcode (if set) gates the expensive actions. No user accounts. |
| `oidc` | Real deployments | OpenID Connect sign-in. **Required** when `APP_ENV=production`; the app refuses to start otherwise. |
| `test` | Automated tests | A built-in fake provider (`POST /auth/test-login`). Refused in production. |

`oidc` needs `OIDC_ISSUER`, `OIDC_CLIENT_ID`, `AUTH_SECRET_KEY` (at least 32 characters, signs the short login-flow cookie) and, for a confidential client, `OIDC_CLIENT_SECRET`. `OIDC_INTERNAL_ISSUER` lets the backend reach the provider at an in-network address while browsers use the public one. `PUBLIC_ORIGIN` is the address people use, and decides the callback `{PUBLIC_ORIGIN}/api/v1/auth/callback` unless `OIDC_REDIRECT_URI` says otherwise. Set `AUTH_COOKIE_SECURE=true` and `SESSION_COOKIE_SECURE=true` behind HTTPS.

## Try it locally with Keycloak (Compose)

```sh
set -a && . ./.env.auth-demo && set +a
docker compose -f docker-compose.yml -f docker-compose.auth.yml up -d --build
# Open http://localhost:8080 and sign in as alice or bob with the local demo password.
```

The realm (`deploy/keycloak/realm-policypilot.json`) defines a public client with PKCE and two users whose passwords come from the environment. Nothing secret is committed. The same realm is used by the kind overlay.

### PolicyPilot login theme

Local Compose mounts the `policypilot` Keycloak login theme from `deploy/keycloak/themes`. It uses the PolicyPilot mark, bundled Manrope and DM Mono fonts, and local CSS only. It does not fetch fonts, images, or styles from a third party. The theme provides a centered branded sign-in and registration experience, respects system dark mode, and is responsive on a narrow viewport.

The committed realm keeps registration and password reset disabled. Local Compose alone starts a short-lived `keycloak-init` helper after Keycloak is available. That helper enables registration for local browser verification, while leaving password reset disabled. The kind overlay remains registration-disabled and mounts the same theme assets through its `keycloak-theme` ConfigMap.

To install this theme on another Keycloak instance, copy `deploy/keycloak/themes/policypilot` into that instance's `/opt/keycloak/themes` directory, set the realm's `loginTheme` to `policypilot`, and restart Keycloak. Existing Keycloak data is not re-imported when the realm JSON changes, so update an existing development realm with the admin console or recreate only the local development realm when a fresh import is required.

## What a request goes through

1. The browser asks `/api/v1/auth/me`. With `mode=oidc` and nobody signed in, the app shows the sign-in screen.
2. **Sign in** goes to `/api/v1/auth/login`, which sends the browser to the provider with PKCE, `state` and `nonce`, and a short-lived signed cookie remembering them.
3. The provider redirects to `/api/v1/auth/callback`. The server checks `state` against the cookie, exchanges the code (with the PKCE verifier), validates the ID token (signature from the provider's key set, algorithm allow-list, issuer, audience, expiry, `nonce`) and only then creates or finds the user and issues its own cookie.
4. Every other route (`/sessions`, `/documents`, `/turns`, the PDF viewer and the event stream) requires that cookie. A conversation cookie only names a conversation; it is honoured only if the signed-in user owns it, otherwise the answer is the same 404 as for a conversation that does not exist.
5. **Sign out** revokes the server-side login. Open event streams end within about five seconds. An expired login behaves the same way and the UI says "Your sign-in ended".
6. Signing in again picks the person's latest conversation back up (`/auth/me` returns its id, `POST /sessions/{id}/resume` re-attaches it).

## Who can see what

| Data | Visible to |
|---|---|
| The 14 bundled documents (10 synthetic policies, 4 NIST references) | Any signed-in user |
| An uploaded PDF, its pages, its file, its ingestion progress | Only the user who owns the conversation it was uploaded to |
| Conversations, turns, traces, citations | Only their owner |
| Search results and cached results | Only what the asker may see: cache keys include the conversation, so one person's upload never appears in another's results |

Rows created before sign-in existed have no owner and are never given to anyone.

## What was tested

`backend/tests/integration/test_auth.py` runs the backend against a real local OpenID Connect provider (RSA-signed tokens, PKCE verified) and covers: a successful sign-in; protected routes returning 401 when signed out; a forged `state`; a wrong nonce, issuer or audience, an expired token and a bad signature; a replayed code; a provider outage (503, not a hang); logout revoking the login server-side; an expired login; cross-site requests refused; two users unable to read each other's conversation, upload, pages, file or ingestion run (including presenting the other's conversation id as a cookie); resuming a conversation after signing in again; production refusing to start without real sign-in. The Keycloak flow in a browser, including two users, is in `docs/deployment-evidence/`.

## Not done

- Single logout (the provider's own session stays open after signing out of PolicyPilot).
- Roles. Every signed-in user can read the shared corpus and nobody can administer it from the UI; corpus changes are a deployment action.
- Trying it against a university identity provider.
- Rate limits are still per client address, not per user.
