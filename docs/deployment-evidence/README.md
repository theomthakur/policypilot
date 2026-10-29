# Deployment evidence

Add redacted evidence from the final immutable release here. Do not add API keys, passcodes, IP allowlists, database credentials, session cookies, full prompts, or private host details.

Required files:

- `release.txt`: UTC time, Git commit SHA, Git tag, backend/frontend image names and digests.
- `health.json`: public readiness response.
- `compose-ps.txt`: service health with sensitive fields removed.
- `smoke-test.txt`: successful end-to-end upload/question/citation output.
- `persistence-check.txt`: before/after restart result.
- `redis-outage.txt`: degraded health and successful fallback result.
- `update-rollback.txt`: release tags used and successful smoke checks after update and rollback.
- `screenshots/`: clean-browser application, trace, and citation drawer.

All evidence remains pending until the production deployment is performed.
