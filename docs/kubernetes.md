# Kubernetes deployment

Decision record: [ADR 0011](adr/0011-kubernetes-deployment.md). Docker Compose remains the required, primary path; this is a second path that was **actually deployed and drilled** on a local `kind` cluster. Evidence from that run (versions, image digests, live security settings, drill output, screenshots) is in [`docs/deployment-evidence/2026-10-30/`](deployment-evidence/2026-10-30/).

## Run it

```sh
# needs docker, kind (https://kind.sigs.k8s.io), kubectl; LLM_API_KEY in the environment or .env
scripts/k8s_up.sh          # cluster, images, ingress controller, generated secrets, deploy, wait
scripts/k8s_smoke.sh       # checks from outside and inside
scripts/k8s_recovery.sh    # failure drills (below)
scripts/k8s_up.sh down     # delete the cluster
```

Then open http://localhost:8088/ and sign in as `alice` or `bob` (generated passwords are in `.k8s-demo-credentials`, mode 0600, git-ignored). Browser walkthrough: `cd scripts/e2e && npm i && npx playwright install chromium && node flow.mjs --help` (see the header comment).

## What is deployed (`deploy/k8s/`)

| Piece | Kind | Notes |
|---|---|---|
| `base/` | Kustomize base | namespace (Pod Security `restricted`), config, PostgreSQL + pgvector and Redis StatefulSets with PVCs, migration Job, seed Job, API, worker, frontend |
| `overlays/kind/` | Overlay (tested) | Keycloak (development identity provider), Ingress, cluster-specific URLs |
| `overlays/openshift/` | Overlay (**rendered only, never deployed**) | arbitrary user IDs, a Route; no database, no identity provider |
| `components/network-policies/` | Opt-in component | default-deny plus the real connections; see "NetworkPolicy" |

- **Order of events:** the migration Job and the seed Job run per release; the API, worker and seed pods wait (init container `wait-schema`) until the schema is at the latest migration. Concurrent seeders are serialized by a PostgreSQL advisory lock. The 14 documents ship as the image `policypilot-corpus` and are copied out at start; nothing is mounted from a host.
- **Secrets** (`policypilot-secrets`, `keycloak-secrets`) are created by `scripts/k8s_up.sh` from random values and your `LLM_API_KEY`; none is in the repository, in the evidence files or in a screenshot.
- **Probes:** startup, liveness and readiness are different checks. Readiness is `/api/v1/health/ready` (database, migrations, Redis, model configuration), which never calls the model. A Redis outage reports degraded and keeps serving; a database outage makes the pod not ready.
- **Hardening applied to every workload:** non-root, all capabilities dropped, no privilege escalation, default seccomp profile, no service-account token. Read-only root filesystem everywhere except PostgreSQL and Keycloak, which write to their own directories (`cluster-facts.md` lists the live values).
- **Traffic:** the Ingress sends everything to nginx in the frontend pods, which proxies `/api` to the API, so the browser sees one origin and event streams and PDF downloads carry the sign-in cookie. Streaming timeouts are raised and buffering is off.

## Drills (run on the cluster, output in `kind-drills.txt`)

| Drill | Result |
|---|---|
| Delete the API pod | a new pod (new UID) serves again in about 6 s |
| Delete the Redis pod | a new pod is ready in a few seconds; the API stays ready (degraded mode falls back to PostgreSQL) |
| Delete the PostgreSQL pod | a new pod mounts the same volume; all documents survive |
| Deploy a bad image tag | the new pod fails to start, the old pod keeps serving (no lost traffic), `kubectl rollout undo` restores the previous image |
| `pg_dump` then restore into a scratch database | the restored database holds the same document count |
| **SIGKILL the worker process while a question is being answered** | the job's lease runs out, the restarted worker claims it (attempt 2, fence 2), the trace shows a `turn_resumed` marker, and the question is answered (108 s, dominated by the 90 s lease) |

A graceful worker shutdown (`SIGTERM`) lets a running job finish within 20 seconds, so a rolling restart does not repeat work; only a crash does.

Application rollback and database rollback are separate operations. Migrations are expand-and-contract, so rolling the image back does not require undoing a migration; there is no automatic destructive downgrade.

## What this does not do

- **No horizontal scaling of the API or worker.** Uploads sit on a ReadWriteOnce volume that the API and worker share, so both run as one replica on one node (the worker has a pod affinity to the API). The next step is an object-storage adapter (S3-compatible, MinIO locally) behind the existing storage path plus a load test; only then is a HorizontalPodAutoscaler honest. None is shipped. The frontend has two replicas, which proves nothing about the backend's scaling.
- **No database high availability.** One PostgreSQL pod with a PVC survives pod and process restarts; it does not survive losing the node's disk. A managed database or an operator, with point-in-time backups, is the production design; `pg_dump` is shown only as a drill.
- **NetworkPolicy is written but its enforcement was not demonstrated.** The component is valid and renders. On this `kind` cluster (kindnet's policy engine) it made fresh connections unreliable: in a controlled test **7 of 40** new connections from the API to Keycloak failed and 17 took over a second, versus 0 of 40 with the policies removed. The kind overlay therefore leaves the component out, and the cluster in the evidence ran without network policies. To use them, run a CNI with solid policy support (for example Calico or Cilium) and enable the component. Standard NetworkPolicy also cannot allow `openrouter.ai` by name: egress to the model provider is port 443 to any public address; an egress proxy or a CNI-specific FQDN policy is the production control.
- **OpenShift:** the overlay renders and its changes are the standard ones (no fixed user IDs, group-0 writable directories in the image, a Route) but nothing was run on OpenShift. PostgreSQL and Redis there should be managed services or operator-run.
- **HTTPS:** the demo is plain HTTP on localhost, so cookies are not marked `Secure`; set `AUTH_COOKIE_SECURE` and `SESSION_COOKIE_SECURE` behind TLS.
