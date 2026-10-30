# 0010. Durable jobs in PostgreSQL, with a separate worker

**Status:** Accepted, 2026-10-30. Replaces the in-process `asyncio.create_task` and API background tasks.

## Context
A turn or an ingestion started inside the API process died with the process. A restart left a turn `running` forever, and two API replicas could not share work. Redis is a cache and may be lost without losing data, so it should not be the source of truth for work.

## Decision
A `jobs` table in PostgreSQL holds turns and ingestions. The API creates the job in the same transaction as the turn or document, so a job exists if and only if the work does. Workers claim with `FOR UPDATE SKIP LOCKED`, take a lease, extend it with a heartbeat, and finish only while they still hold the job's **fence** (a counter bumped on every claim), so a stalled worker can never overwrite its replacement.
- A job whose lease runs out is claimed again, up to `JOB_MAX_ATTEMPTS`; after that it is ended as interrupted and its turn or document is marked failed with an honest message.
- Delivery is **at least once**. A model call may be repeated (and billed twice) after a crash. Handlers are idempotent: a turn that is already finished returns immediately, a resumed turn adds a visible `turn_resumed` event and continues its numbering, and the final answer is written under a row lock so there is one.
- `POST /sessions/{id}/messages` accepts an `Idempotency-Key`; a retry returns the same turn.
- On shutdown a worker stops claiming, lets running jobs finish for 20 seconds and hands the rest back without using an attempt.
- The API embeds a worker by default (one process, Compose unchanged). `WORKER_EMBEDDED=false` plus `python -m app.jobs.worker` runs it separately, as in Kubernetes. Migrations and corpus seeding can run as their own steps (`RUN_MIGRATIONS_ON_START=false`, `python -m app.cli seed`, with an advisory lock against concurrent seeders).

## Alternatives considered
- **Redis queue (RQ/Celery):** a Redis outage would stop all work and losing Redis would lose jobs.
- **Temporal or a workflow engine:** the right tool at larger scale; far more infrastructure than one small app needs.

## Consequences
- Restarting any process no longer loses accepted questions or uploads.
- Uploaded PDFs are on a local volume by default. `STORAGE_BACKEND=s3` stores them in an S3-compatible bucket (tested against SeaweedFS and an S3 emulator), and a worker then fetches the PDF from the bucket, so API and workers need no shared disk. Without it the Kubernetes manifests pin the worker to the API's node ([0011](0011-kubernetes-deployment.md)).
