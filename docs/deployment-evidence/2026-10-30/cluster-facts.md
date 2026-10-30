# Cluster facts (2026-10-30)

```
release commit: 94b0fc9bb17453531083b8584561df45bf669b16
kind: kind v0.24.0 go1.22.6 darwin/arm64
kubernetes server: v1.31.0
node image: kindest/node:v1.31.0@sha256:53df588e04085fd41ae12de0c3fe4c72f7013bba32a20e7325357a1ac94ba8
policypilot-backend:local sha256:05494e4e33331148e880d49cb272fb580c1ecb1b25aac218a3c86caeec475369
policypilot-frontend:local sha256:cb3542fceb2084c09ceb7b52fa6f142cf329c63f893c766675503c241107436c
policypilot-corpus:local sha256:6136bd1522c2912d844ff7bd6417d4dbe9b6eafa98b7d955ca6a7039e398f507
keycloak: quay.io/keycloak/keycloak:26.0
postgres: pgvector/pgvector:pg16
redis: redis:7.4-alpine
ingress-nginx: registry.k8s.io/ingress-nginx/controller:v1.11.2
```

## Pods
```
api-9984dccbd-fgcwm 1/1 Running restarts=0
frontend-648f8745d9-6p7gs 1/1 Running restarts=0
frontend-648f8745d9-svh4f 1/1 Running restarts=0
keycloak-d4c6b496b-dqksq 1/1 Running restarts=0
policypilot-migrate-m6bx8 0/1 Completed restarts=3
policypilot-seed-b29s7 0/1 Completed restarts=2
postgres-0 1/1 Running restarts=0
redis-0 1/1 Running restarts=0
worker-7754667f5b-wtnr4 1/1 Running restarts=1
```

## Security settings actually applied (from the live pods)
```
api-9984dccbd-fgcwm          api       nonroot= True uid= 999 readOnlyRoot= True dropALL= True noPrivEsc= True
frontend-648f8745d9-6p7gs    frontend  nonroot= True uid= 101 readOnlyRoot= True dropALL= True noPrivEsc= True
frontend-648f8745d9-svh4f    frontend  nonroot= True uid= 101 readOnlyRoot= True dropALL= True noPrivEsc= True
keycloak-d4c6b496b-dqksq     keycloak  nonroot= True uid= 1000 readOnlyRoot= None dropALL= True noPrivEsc= True
policypilot-migrate-m6bx8    migrate   nonroot= True uid= 999 readOnlyRoot= True dropALL= True noPrivEsc= True
policypilot-seed-b29s7       seed      nonroot= True uid= 999 readOnlyRoot= True dropALL= True noPrivEsc= True
postgres-0                   postgres  nonroot= True uid= 999 readOnlyRoot= None dropALL= True noPrivEsc= True
redis-0                      redis     nonroot= True uid= 999 readOnlyRoot= True dropALL= True noPrivEsc= True
worker-7754667f5b-wtnr4      worker    nonroot= True uid= 999 readOnlyRoot= True dropALL= True noPrivEsc= True
```

Namespace Pod Security level: restricted

## Images
```
policypilot-backend:local sha256:05494e4e33331148e880d49cb272fb580c1ecb1b25aac218a3c86caeec475369
policypilot-frontend:local sha256:cb3542fceb2084c09ceb7b52fa6f142cf329c63f893c766675503c241107436c
policypilot-corpus:local sha256:6136bd1522c2912d844ff7bd6417d4dbe9b6eafa98b7d955ca6a7039e398f507
```

Postgres and Keycloak run non-root with all capabilities dropped but without a read-only root filesystem (PostgreSQL and Keycloak write to their own directories); Redis, the API, worker, frontend and both Jobs have one.

## Smoke test
```
ok   every pod is ready
ok   frontend answers through the ingress
ok   API ready: {"status":"ok","version":"0.1.0","checks":{"database":"ok","migrations":"ok","redis":"ok","llm_config":"ok"},"corpus_documents":14}
ok   documents need a sign-in (401 when signed out)
ok   login redirects to the identity provider
ok   14 shared documents are searchable
ok   schema at c3d4e5f6a7b8
smoke passed
```
