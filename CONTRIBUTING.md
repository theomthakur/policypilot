# Contributing

## Workflow
1. Every change starts from a GitHub issue (template: Task or Bug) linked to a milestone (M0 to M7).
2. Branch from `main`: `ws1/<short-name>`, `ws2/<short-name>` or `ws3/<short-name>`. Keep branches short-lived.
3. Edit only your workstream's paths (see `.github/CODEOWNERS` and the workstream briefs). Changes to `contracts/` need review from every affected workstream.
4. Commit small, logical changes with their tests, and push after every commit. Open a draft pull request early.
5. Rebase on `main` before marking the PR ready. CI must be green. Another reviewer and the owner approve.
6. Merge with **merge commits or rebase-and-merge**. Squash merging is disabled so every commit stays visible.

## Commit messages (Conventional Commits)
`type(scope): summary (#issue)`

Types: `feat`, `fix`, `test`, `docs`, `refactor`, `perf`, `build`, `ci`, `chore`.

Examples:
- `feat(retrieval): fuse vector and full-text results with RRF (#12)`
- `test(tools): cover empty and invalid-argument envelopes (#14)`
- `fix(agent): block duplicate tool calls in the same turn (#21)`

Commits are real and made as the work happens: no back-dated timestamps or rewritten authorship.

## Definition of Done
- Merged to `main` through a reviewed PR.
- Tests added and passing in CI; lint and type checks clean.
- Relevant docs updated; requirement IDs ticked in `docs/requirements.md`.
- No secrets committed.

## Local checks
- Install hooks once: `pip install pre-commit && pre-commit install`
- Backend: `cd backend && ruff check . && ruff format --check . && mypy app && pytest`
- Frontend: `cd frontend && npm run lint && npm run typecheck && npm test`

## AI assistance
AI coding tools are used in this project, as the assignment allows. Each PR notes which tool helped and what was reviewed or changed by hand. Coding-agent transcripts are kept in `docs/agent-logs/`.
