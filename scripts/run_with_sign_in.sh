#!/bin/sh
# Start the full stack with real sign-in (Keycloak) and the themed login and registration pages.
# First run creates .env.auth-demo (git-ignored) with random passwords for the test users alice and bob.
# Usage: scripts/run_with_sign_in.sh          then open http://localhost:8080
# To go back to the plain demo without sign-in: docker compose up -d
set -eu
cd "$(dirname "$0")/.."
if [ ! -f .env.auth-demo ]; then
  umask 077
  {
    echo "KC_ALICE_PASSWORD=$(openssl rand -hex 8)"
    echo "KC_BOB_PASSWORD=$(openssl rand -hex 8)"
    echo "AUTH_SECRET_KEY=$(openssl rand -hex 32)"
  } > .env.auth-demo
  echo "Created .env.auth-demo (the test users' passwords are in it)."
fi
set -a
. ./.env.auth-demo
set +a
docker compose -f docker-compose.yml -f docker-compose.auth.yml up -d --build
echo "Sign in at http://localhost:8080 as alice or bob (passwords in .env.auth-demo), or choose Create account."
