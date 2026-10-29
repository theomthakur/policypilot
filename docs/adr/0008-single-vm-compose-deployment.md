# 0008. Single VM, same Compose file, Caddy

**Status:** Accepted, 2026-10-29

## Context
The stack must run through Docker Compose, and the app will also be deployed publicly for a demo.

## Decision
Deploy the same Compose stack to one Ubuntu VM (about 2 vCPU, 4 GB RAM), adding a `caddy` service in `compose.prod.yaml` for automatic HTTPS, security headers and request-size limits. Public use is protected by a demo passcode, Redis-backed rate limits, a daily model-spend cap and a provider key with a hard spending limit.

## Alternatives considered
- **Managed platforms** (Render, Railway, Fly): less server work, but they don't run Compose files directly, so the deployment would differ from the documented stack.
- **Kubernetes or OpenShift:** an optional enhancement in the brief; excessive for one small app.

## Consequences
- The runbook is the same for local and production use.
- One machine is a single point of failure; the scaling path (managed Postgres and Redis, API replicas, worker-based ingestion) is documented.
