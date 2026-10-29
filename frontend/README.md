# PolicyPilot frontend

React and TypeScript interface for document upload, agent conversations, page citations, and safe execution traces.

## Requirements

- Node.js 22.12 or newer
- npm 10 or newer

## Run against the included mock API

Use two terminals from `frontend/`:

```sh
npm install
npm run mock
```

```sh
npm run dev
```

Vite serves the UI at `http://localhost:5173` and proxies `/api` to the mock API at `http://localhost:4010`.

## Checks

```sh
npm run lint
npm test
npm run build
npm run format:check
```

## API contract

When WS1 publishes `contracts/openapi.yaml`, generate contract types with:

```sh
npm run generate:api
```

`src/api/types.ts` is the temporary Phase 0 compatibility layer based on the shared execution-plan contract summary. Replace it with aliases to `schema.generated.ts` during WS2-50, after the OpenAPI contract lands. Do not change the shared contract from this workstream.

## Production image

The multi-stage Dockerfile compiles the app and serves it from unprivileged nginx on port 8080. `nginx.conf` proxies `/api/` to `backend:8000`, disables buffering for server-sent events, and falls back to `index.html` for client routes.
