# Security and limitations

## Security boundaries

PolicyPilot is a read-only question-answering demo. The agent can list indexed documents, search corpus chunks, and read bounded page ranges. It cannot browse the web, execute document content, write files, send messages, run SQL, or take external actions.

Uploaded and retrieved text is untrusted data. The agent prompt and tool wrappers preserve the distinction between application instructions and document evidence. The planted prompt-injection case verifies that retrieved commands are neither followed nor repeated as an answer.

## Controls

- Pydantic validates model-generated tool arguments.
- Tools accept corpus-scoped IDs, not arbitrary paths or URLs.
- SQL is parameterized through the backend data layer.
- Uploads are restricted by MIME/type, size, page count, generated storage name, and text extraction.
- Agent steps, tool calls, revisions, retries, tool duration, total turn duration, and token use are bounded.
- Citation IDs must refer to evidence observed in the current turn; document/page/quote provenance is verified before display.
- Sessions use unguessable IDs and an HttpOnly binding. Production cookies are secure and same-site.
- The public demo requires a passcode (an operational cost gate), per-client rate limits, a daily application budget, and a provider-side capped key.
- Real deployments sign people in through OpenID Connect (Authorization Code with PKCE, state and nonce, ID-token validation, server-side revocable sessions); every conversation, upload and trace belongs to one user, and the API refuses to start in production without sign-in ([authentication](authentication.md)). State-changing requests that carry the sign-in cookie must originate from this site.
- Each Kubernetes workload runs non-root with all capabilities dropped and no service-account token ([kubernetes](kubernetes.md)).
- Caddy terminates TLS, restricts request bodies, and sets HSTS, CSP, frame, MIME, referrer, and permission headers.
- Logs carry correlation IDs and operational summaries. They must not contain keys, passcodes, full hidden prompts, private chain-of-thought, or complete documents.
- PostgreSQL is durable. Redis contains replaceable expiring snapshots/caches and has a documented degraded fallback.
- Containers use pinned major/minor images, non-root application users, explicit health checks, and persistent named volumes.

## Threats considered

| Threat | Primary mitigation | Residual risk |
|---|---|---|
| Prompt injection in PDFs | Instruction/data boundary, read-only tools, bounded outputs, CASE-7 | Models can still mishandle novel adversarial wording |
| Fabricated citations | Evidence IDs plus page and quote verification | Exact quote presence does not prove claim entailment |
| Cross-session access | Session binding and corpus visibility checks | Demo access control is not enterprise authorization |
| Malicious PDF | No execution, generated filenames, limits, text-only parser | Parser vulnerabilities and decompression attacks require ongoing patching/sandboxing |
| API cost abuse | Passcode, Redis limits, token/step limits, daily cap, capped key | Shared passcodes can leak; in-process fallback is weaker during Redis outage |
| Dependency outage | Timeouts, one retry, partial result, Redis fallback | Model or database outage can still prevent an answer |
| Secret disclosure | Environment-only secrets, redacted logs, gitleaks | Operator error remains possible |

## Known limitations

- Only text-based PDFs are supported; scanned documents require OCR outside this submission.
- The synthetic corpus is small and does not represent real NYU policy or production diversity.
- Hybrid retrieval and thresholds are tuned on a small evaluation set and may not generalize.
- Hosted model behavior can change despite fixed identifiers; seed support is best effort.
- Citation verification checks provenance and text overlap, not semantic entailment.
- The one-VM deployment has a single failure domain and limited vertical capacity.
- Sign-in is implemented and tested against Keycloak, not against a university identity provider. There are no roles, single logout is not implemented, and rate limits are per client address, not per user. With `AUTH_MODE=off` (the default Compose demo) only the shared passcode gates access.
- A job can run twice after a crash: delivery is at least once, so a model call may be repeated and billed twice. The final answer is still written once.
- Kubernetes: one PostgreSQL pod is durable but not highly available; the API and worker are single replicas sharing a ReadWriteOnce volume; NetworkPolicies are written but their enforcement was not demonstrated (kindnet made connections unreliable); the OpenShift overlay was never deployed.
- Redis fallback preserves core behavior but loses distributed rate-limit precision and caching.
- PDF files reside on a Docker volume/local disk. Production should use encrypted object storage and malware scanning.
- Logs and health endpoints are sufficient for the take-home; production needs centralized metrics, traces, alerts, and audit retention.
- Backups are local until copied off-host. A production service needs encrypted remote backups and scheduled restore drills.

## Production path

For broader use, add institutional identity, tenant/corpus authorization, object storage, asynchronous ingestion workers, managed PostgreSQL and Redis, malware scanning, OCR isolation, centralized observability, secret management, backup automation, and multiple stateless API replicas behind a load balancer.
