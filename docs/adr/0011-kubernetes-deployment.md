# 0011. Kubernetes as a second, tested deployment path

**Status:** Accepted, 2026-10-30. Docker Compose stays the required path; see [0008](0008-single-vm-compose-deployment.md).

## Context
The brief lists Kubernetes or OpenShift as an optional enhancement, and a deployment that survives pod and node restarts is a good test of the state design.

## Decision
Kustomize: a `base` of plain manifests and a `kind` overlay that was actually deployed and drilled on a local `kind` cluster.
- **Workloads:** frontend (2 replicas), API (1), worker (1), PostgreSQL and Redis as single-replica StatefulSets with PVCs, Keycloak in the overlay only. A one-shot migration Job and an idempotent seed Job run per release; API and worker wait for the schema in an init container. The corpus ships as a versioned image, not a host mount.
- **Safety:** namespace enforces the `restricted` Pod Security level; every pod is non-root, drops all capabilities, has a read-only root filesystem and the default seccomp profile; no pod gets a service-account token; default-deny NetworkPolicies allow only the real connections.
- **Secrets** are generated at deploy time by `scripts/k8s_up.sh` and never committed.
- **Probes** separate startup, liveness (process is alive) and readiness (dependencies reachable); the readiness endpoint does not call the model. A Redis outage is degraded, a database outage is not ready.
- **Rollout:** the API uses a rolling update with no unavailable pods, so a bad image never takes traffic; rollback is `kubectl rollout undo`. Application rollback and database rollback are separate: migrations are expand-and-contract.
- **OpenShift:** an overlay (arbitrary user IDs, a Route instead of an Ingress) that was **rendered but never deployed**.

## What this deliberately does not do
- No horizontal scaling of the API: uploads sit on a ReadWriteOnce volume shared with the worker on one node. Scaling out needs object storage (an S3-compatible adapter, with MinIO locally, is the next step) and a load test. No HorizontalPodAutoscaler is shipped because none was tested.
- No database replication or failover, no Redis Sentinel: the single PostgreSQL StatefulSet is durable (PVC), not highly available. The production answer is a managed or operator-run database.
- NetworkPolicy cannot allow `openrouter.ai` by name; egress to the model provider is port 443 to any public address, and a name-based egress proxy or a CNI-specific policy is the production control.

## Consequences
- The same images run under Compose and Kubernetes. A cluster deployment is reproducible from one command and has recorded drill evidence (`docs/deployment-evidence/`).
