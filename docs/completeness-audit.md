# End-to-end completeness audit

**Audited branch:** `origin/integration/full-stack` at `cab2068`  
**Audit date:** October 29, 2026  
**Verdict:** The integrated project has a substantial working core, but it is not submission-ready. Local containers, ingestion, persistence, Redis fallback, tools, agent mechanics, and UI builds work. Evaluation quality, session authorization, release documentation, deployment evidence, and the official smoke/CI gates remain incomplete.

## What was verified

| Area | Result | Evidence |
|---|---|---|
| Frontend | Pass | ESLint, TypeScript, 10 tests, production build, zero npm audit findings |
| Backend static/unit checks | Pass with warnings | Ruff, strict mypy, 22 tests passed, 2 integration modules skipped by default |
| Backend real integration checks | Pass with warnings | 39 tests passed against real PostgreSQL and Redis when run explicitly with `INTEGRATION=1` |
| Corpus | Pass | 10 text PDFs; deterministic generation and manifest validation |
| Evaluation dataset | Pass | 11 cases validate against the JSON Schema and manifest |
| Compose build/start | Pass | Frontend, backend, PostgreSQL, and Redis built and became container-healthy |
| API route inventory | Pass | All 12 documented method/path pairs exist at runtime after `/api/v1` normalization |
| Corrected API flow | Partial | Upload-to-answer completed with a verified citation, but the answer was factually wrong for the question |
| Redis outage | Pass | Readiness became `degraded`; a turn completed; Redis restarted |
| Persistence | Pass | 10 documents and a created session survived container restart |
| Official smoke script | Fail | Upload returns HTTP 400 because the script does not retain the session cookie |
| Offline 11-case evaluation | Fail | All 20 applicable agent/baseline system-case results failed; CASE-11 also hit the default rate limit |
| Public deployment | Not verified | No live URL or deployment evidence in the integrated branch |

## Submission blockers

### 1. No passing agent-versus-baseline evaluation

There are no committed real-model results. An audit run using the offline extractive model failed all 20 applicable system-case combinations. The failures were not committed as final evidence because they do not represent the required configured model evaluation.

The corrected manual smoke question asked for NorthfieldGuest limits but returned a BYOD passage from page 6. Its quote and page were valid, so citation verification passed while answer correctness failed. This is an important distinction: provenance validation does not prove relevance or entailment.

Required before submission:

- Run the 11 cases with the selected real model.
- Fix retrieval/agent failures against frozen cases without weakening expected checks.
- Commit raw results, aggregate report, representative traces, manual page checks, cost, and failure analysis.
- Include at least one honest remaining failure if one exists.

### 2. Session isolation is incomplete

`GET /sessions/{session_id}`, `GET /turns/{turn_id}`, and the SSE turn stream do not check that the current `pp_session` cookie owns the requested resource. A direct audit request accessed session A with session B's cookie and received HTTP 200.

`POST /sessions/{session_id}/messages` verifies that the session exists but does not bind it to the request cookie. UUID entropy reduces casual discovery but is not authorization. This conflicts with REQ-F7.

Required before public deployment:

- Bind session, turn, event-stream, upload, document, and page access to the current session or an explicit public-corpus policy.
- Add negative integration tests for cross-session session/turn/event access.
- Return a consistent 404 or 403 without revealing resource existence.

### 3. Required release documentation is missing from the integrated branch

Present: `docs/architecture.md`, `docs/presentation.md`, `docs/requirements.md`, ADRs.

Missing:

- `docs/evaluation.md`
- `docs/demo.md`
- `docs/reproducibility.md`
- `docs/runbook.md`
- `docs/security-and-limitations.md`
- `docs/summary.md`
- `docs/deployment-evidence/`

The root README is still a three-paragraph active-development placeholder. It has no usable setup procedure, screenshots, live URL, evaluation headline, reproducibility links, or limitations.

### 4. No deployment or demo evidence

The integrated branch contains no public URL, recorded demo, release SHA evidence, image digests, HTTPS health output, public end-to-end request, update/rollback drill, persistence evidence, or Redis-outage evidence.

Do not claim deployment until the signed-out public flow succeeds against an immutable release tag.

### 5. The official smoke test is broken and too weak

`scripts/smoke_test.sh` uploads before creating a session and does not retain the `pp_session` cookie, so the backend correctly returns HTTP 400.

After that is fixed, the final assertion must check the expected fact and expected document/page, not only that at least one citation reports `verified: true`. The current assertion would accept the factually wrong BYOD answer observed during this audit.

## High-priority gaps

### CI skips the real integration suite

The backend CI job starts PostgreSQL and Redis but does not set `INTEGRATION=1`. As a result, the integration modules are skipped. The 39 integration tests pass when invoked explicitly against real services, so CI should run them rather than silently skip them.

Add a CI assertion that fails if expected integration tests are skipped.

### No automated API contract-drift gate

Runtime and committed route paths currently match, but CI does not compare the generated FastAPI OpenAPI document with `contracts/openapi.yaml`. Schema/error drift can still occur. For example, the implementation returns `PASSCODE_REQUIRED`, while the committed error-code enum uses `UNAUTHORIZED`.

### Evaluation conflicts with the default rate limit

The evaluator runs enough turns to exceed `RATE_LIMIT_PER_MINUTE=20`; CASE-11 received HTTP 429 in the audit run. Add explicit evaluation configuration, controlled pacing, or an authorized evaluation identity with a documented higher limit. Do not disable public rate limiting globally.

### Passcode enforcement does not match the contract description

The OpenAPI description says every public request requires `X-Demo-Passcode`. The backend enforces it only when starting a message. Session creation, document listing/page access, session history, turn reads, and event streams are not covered by the same gate.

Choose and document one policy, then enforce it centrally and test it.

### Production images are not published

The production Compose overlay expects immutable GHCR backend/frontend images. CI currently builds images with `push: false`; no release workflow or documented manual image publication exists on the integrated branch.

### Work is not on `main`

Remote `main` remains the initial commit. The integrated work is on `integration/full-stack`, and this favicon/audit change is on `fix/favicon-and-audit`. Merge through reviewed pull requests, run CI, and tag the tested release before submission.

## Medium-priority issues

- `docs/requirements.md` still marks every requirement and submission item `planned`, despite implemented and tested features.
- Readiness always returns `corpus_documents: null`; expose the actual ready corpus count or remove the field.
- Default local `.env.example` selects `openai_compatible` without a key. The documented three-command quick start should deliberately select offline/fake mode or instruct the user to set a key.
- Pytest reports an unset async fixture loop-scope deprecation and Starlette's deprecated TestClient/httpx integration. These do not fail today but should be pinned/configured before future upgrades.
- Pre-commit uses Ruff 0.8.4 while the locked backend environment currently resolves a newer Ruff. Align local and CI tool versions.
- CI runs no explicit Python or container dependency vulnerability audit, even though the planning document calls for one.
- The health check marks the backend container healthy by liveness, not readiness. Compose can therefore appear healthy while migrations/database/model readiness is down.

## Favicon and logo correction

The old 192×193 PNG used only the central 141×142 alpha bounds, leaving roughly one-quarter of the canvas as transparent padding. The new SVG uses a tight `-33 -33 66 66` viewBox, thicker petals, no background box, and fills the browser favicon canvas. The header, launch, and passcode marks were also changed to remove their surrounding boxes and orbit circles while increasing their rendered size.

## Recommended completion order

1. Fix session/turn authorization and add cross-session tests.
2. Fix smoke-test cookie handling and assert the exact expected fact/page.
3. Set CI to execute, not skip, the 39 integration tests; add contract-drift checking.
4. Run the real model against CASE-1 first and repair retrieval before running all 11 cases.
5. Add evaluation pacing/configuration so the rate limiter does not invalidate CASE-11.
6. Complete and integrate the missing README and release documentation.
7. Run and commit real evaluation results plus manual page checks.
8. Publish immutable images, deploy behind HTTPS/passcode/cost caps, and capture all runbook evidence.
9. Record the required demo from the deployed release.
10. Update the requirement matrix, merge to `main`, tag the release, verify links signed out, and submit.
