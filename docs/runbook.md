# Deployment and operations runbook

This runbook deploys PolicyPilot to one Ubuntu 24.04 VM with Docker Compose and Caddy. It is appropriate for a low-traffic interview demo, not a high-availability production service.

## 1. Target and prerequisites

Recommended minimum:

- Ubuntu 24.04 LTS, 2 vCPU, 4 GB RAM, 40 GB encrypted disk.
- Static public IP and a dedicated DNS name.
- Cloud firewall: TCP 80/443 from the internet; TCP 22 only from the maintainer's IP.
- SSH key authentication, non-root deploy user, unattended security updates.
- Docker Engine with Compose plugin.
- A provider project key with a hard spending limit.
- GitHub Container Registry read access if the images are private.

The base Compose stack runs PostgreSQL, Redis, FastAPI, and React/nginx. The production overlay adds Caddy. PostgreSQL, Redis, uploaded PDFs, and Caddy state use named volumes.

## 2. One-time host setup

Run as an authorized sudo user on the new VM. Review Docker's current Ubuntu installation instructions before using a public service.

```sh
sudo apt-get update
sudo apt-get install -y ca-certificates curl git jq unattended-upgrades
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
. /etc/os-release
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $VERSION_CODENAME stable" | sudo tee /etc/apt/sources.list.d/docker.list >/dev/null
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo usermod -aG docker "$USER"
```

Log out and back in, then verify:

```sh
docker version
docker compose version
```

Point the DNS `A` record at the VM before initial deployment. Caddy needs ports 80 and 443 to obtain a certificate.

## 3. Production configuration

Clone into a deploy-user-owned path and check out an immutable release tag:

```sh
git clone https://github.com/theomthakur/policypilot.git
cd policypilot
git fetch --tags --prune
git checkout v1.0.0-rc.1
```

Create `.env` without printing secrets into shell history. At minimum set:

```dotenv
APP_ENV=production
APP_VERSION=1.0.0-rc.1
LOG_LEVEL=INFO
PUBLIC_ORIGIN=https://policy.example.edu
DEMO_PASSCODE=<long-random-demo-code>
SESSION_COOKIE_SECURE=true
POSTGRES_DB=policypilot
POSTGRES_USER=policypilot
POSTGRES_PASSWORD=<long-random-database-password>
REDIS_URL=redis://redis:6379/0
LLM_PROVIDER=openai_compatible
LLM_BASE_URL=https://openrouter.ai/api/v1
LLM_API_KEY=<capped-public-project-key>
LLM_MODEL=openai/gpt-4o-mini
EMBEDDING_PROVIDER=local
EMBEDDING_MODEL=BAAI/bge-small-en-v1.5
RATE_LIMIT_PER_MINUTE=20
DAILY_BUDGET_USD=1.00
FAULT_INJECTION_ENABLED=false
DOMAIN=policy.example.edu
ACME_EMAIL=operator@example.edu
IMAGE_TAG=<immutable-release-tag-or-commit-sha>
```

Then restrict it:

```sh
chmod 600 .env
```

Never enable fault injection on the public service. Never use a personal unrestricted model key.

## 4. Initial deployment

Authenticate to GHCR if image access requires it:

```sh
printf '%s' "$GHCR_TOKEN" | docker login ghcr.io -u theomthakur --password-stdin
unset GHCR_TOKEN
```

Set the immutable image tag and start storage first:

```sh
export IMAGE_TAG=v1.0.0-rc.1
export DOMAIN=policy.example.edu
export ACME_EMAIL=operator@example.edu
docker compose -f docker-compose.yml -f compose.prod.yaml pull postgres redis backend frontend caddy
docker compose -f docker-compose.yml -f compose.prod.yaml up -d postgres redis
docker compose -f docker-compose.yml -f compose.prod.yaml run --rm backend alembic upgrade head
docker compose -f docker-compose.yml -f compose.prod.yaml up -d --remove-orphans --wait
```

Load the bundled corpus through the public API:

```sh
export POLICYPILOT_BASE_URL="https://$DOMAIN/api/v1"
export POLICYPILOT_DEMO_PASSCODE='<demo-code>'
./scripts/seed_corpus.sh
```

Keep the passcode variable only in the current protected shell while completing the verification and drills below. Unset it when the work is finished:

```sh
unset POLICYPILOT_DEMO_PASSCODE
```

## 5. Deployment verification

Record the exact release:

```sh
git rev-parse HEAD
git describe --tags --always
docker compose -f docker-compose.yml -f compose.prod.yaml images --format json
docker compose -f docker-compose.yml -f compose.prod.yaml ps
```

Verify TLS and health:

```sh
curl --fail --show-error --silent "https://$DOMAIN/healthz"
curl --fail --show-error --silent \
  -H "X-Demo-Passcode: $POLICYPILOT_DEMO_PASSCODE" \
  "https://$DOMAIN/api/v1/health/ready" | jq .
```

Run the end-to-end smoke test:

```sh
POLICYPILOT_BASE_URL="https://$DOMAIN/api/v1" \
POLICYPILOT_DEMO_PASSCODE="$POLICYPILOT_DEMO_PASSCODE" \
./scripts/smoke_test.sh
```

Use a clean browser to confirm the passcode gate, document list, one question, trace events, and a highlighted citation page. Save redacted outputs to `docs/deployment-evidence/`.

## 6. Persistence drill

The script creates a session, records document count, restarts all stateful/application containers without removing volumes, and verifies both values:

```sh
POLICYPILOT_BASE_URL="https://$DOMAIN/api/v1" \
POLICYPILOT_DEMO_PASSCODE="$POLICYPILOT_DEMO_PASSCODE" \
./scripts/persistence_check.sh
```

Never use `docker compose down -v` on a deployment whose data must survive.

## 7. Redis outage drill

The script stops Redis, checks for `degraded` readiness, asks a question through the PostgreSQL/uncached fallback, and restarts Redis via a shell trap:

```sh
POLICYPILOT_BASE_URL="https://$DOMAIN/api/v1" \
POLICYPILOT_DEMO_PASSCODE="$POLICYPILOT_DEMO_PASSCODE" \
./scripts/redis_outage.sh
```

Expected behavior:

- Readiness remains available with `status: degraded` and `checks.redis: down`.
- Existing durable sessions and document indexes remain accessible.
- Search runs without Redis cache.
- Rate limiting falls back to the documented conservative in-process behavior.
- Redis restart restores normal readiness without manual data repair.

## 8. Backups and restore rehearsal

Create a compressed logical database backup and checksum:

```sh
BACKUP_DIR=/srv/policypilot-backups ./scripts/backup.sh
```

Copy backups to encrypted off-host storage in a real production environment. Uploaded source PDFs are reproducible for the bundled corpus; separately archive user uploads if they must be retained.

Restore is destructive to the selected database and therefore requires an explicit guard:

```sh
shasum -a 256 -c /srv/policypilot-backups/policypilot-<timestamp>.sql.gz.sha256
CONFIRM_RESTORE=policypilot ./scripts/restore.sh /srv/policypilot-backups/policypilot-<timestamp>.sql.gz
```

Perform a restore rehearsal against a temporary database first. Verify the target host, database, and backup timestamp before setting `CONFIRM_RESTORE`.

## 9. Updating

Use expand-and-contract migrations so the old and new application versions can both use the migrated schema.

```sh
export OLD_TAG="$(git describe --tags --always)"
export NEW_TAG=v1.0.0-rc.2
BACKUP_DIR=/srv/policypilot-backups ./scripts/backup.sh
git fetch --tags --prune
git checkout "$NEW_TAG"
export IMAGE_TAG="$NEW_TAG"
docker compose -f docker-compose.yml -f compose.prod.yaml pull backend frontend
docker compose -f docker-compose.yml -f compose.prod.yaml run --rm backend alembic upgrade head
docker compose -f docker-compose.yml -f compose.prod.yaml up -d --no-deps backend frontend --wait
POLICYPILOT_BASE_URL="https://$DOMAIN/api/v1" POLICYPILOT_DEMO_PASSCODE="$POLICYPILOT_DEMO_PASSCODE" ./scripts/smoke_test.sh
```

If the smoke test fails, use the rollback procedure immediately.

## 10. Rolling back

Application rollback normally does not restore the database because migrations must be backward compatible.

```sh
git checkout "$OLD_TAG"
export IMAGE_TAG="$OLD_TAG"
docker compose -f docker-compose.yml -f compose.prod.yaml pull backend frontend
docker compose -f docker-compose.yml -f compose.prod.yaml up -d --no-deps backend frontend --wait
POLICYPILOT_BASE_URL="https://$DOMAIN/api/v1" POLICYPILOT_DEMO_PASSCODE="$POLICYPILOT_DEMO_PASSCODE" ./scripts/smoke_test.sh
```

Restore a database backup only when an explicitly documented irreversible migration requires it, after taking the service out of traffic and confirming the target. The take-home release should contain no irreversible destructive migration.

## 11. Logs and diagnosis

```sh
docker compose -f docker-compose.yml -f compose.prod.yaml ps
docker compose -f docker-compose.yml -f compose.prod.yaml logs --since=30m --tail=300 backend
docker compose -f docker-compose.yml -f compose.prod.yaml logs --since=30m --tail=300 postgres redis caddy
```

Use request, session, and turn correlation IDs. Do not paste secrets, complete document contents, session cookies, or user prompts into tickets or committed evidence.

Disk and volume checks:

```sh
df -h
docker system df
docker volume ls | grep policypilot
```

Do not run prune or volume-deletion commands during incident diagnosis.

## 12. Routine operation

- Check HTTPS, readiness, and model budget before a demonstration.
- Review provider spend and application daily budget after public access.
- Run nightly PostgreSQL backups and monitor their checksums/size.
- Apply OS and container security updates through a tested release.
- Rotate demo passcode and model key after the interview.
- Stop the public service or revoke the model key when the demo window ends.

## 13. Scaling path

The VM is one failure domain. For sustained use:

1. Move PostgreSQL and Redis to managed, encrypted services.
2. Put PDFs in encrypted object storage and add malware scanning.
3. Move ingestion to Redis-backed workers.
4. Run multiple stateless backend/frontend replicas behind a load balancer.
5. Add SSO, corpus-level authorization, centralized logs/metrics/traces, alerts, and managed secrets.
6. Test backup restoration and dependency-failure modes on a schedule.
