# Deployment Runbook

## Backend

Run the FastAPI API as a Docker service with PostgreSQL, Redis, and S3-compatible object storage.

Required services:
- PostgreSQL 16
- Redis 7
- S3-compatible bucket
- API container
- Celery worker
- Celery beat

Required environment:
- Copy `backend/.env.example` and replace every production value.
- Set `TOKEN_ENCRYPTION_SECRET` before any OAuth tokens are stored.
- Set `VIEWER_BASE_URL` to the deployed viewer domain.
- Set `BACKEND_PUBLIC_BASE_URL` to the public API domain.

Railway:
1. Create separate services for API, worker, and beat using `backend/` as the service root.
2. Use `backend/railway.json` for the API service.
3. Override the worker start command with `celery -A app.core.celery_app.celery_app worker --loglevel=info`.
4. Override the beat start command with `celery -A app.core.celery_app.celery_app beat --loglevel=info`.
5. Attach PostgreSQL and Redis plugins, then set S3 credentials.

Fly.io:
1. Run `fly launch` from `backend/`.
2. Use `backend/fly.toml`.
3. Provision Postgres and Redis, then set secrets with `fly secrets set`.
4. Scale process groups separately: `app`, `worker`, and `beat`.

Health check:
- `GET /healthz`

## Viewer

Deploy `viewer/` to Vercel.

Required environment:
- `NEXT_PUBLIC_REBUG_API_BASE_URL=https://api.example.com/api/v1`
- `REBUG_API_BASE_URL=https://api.example.com/api/v1`

Use `viewer/vercel.json` for the build and install commands.

## Chrome Extension

Build:

```bash
cd extension
pnpm install --frozen-lockfile
pnpm build
pnpm zip
```

Upload the generated Chrome MV3 zip from `extension/.output/`.

Production settings:
- Set the backend URL in the popup Settings tab.
- Add the production API origin to extension host permissions before store submission if narrowing from `<all_urls>`.

## OAuth Callback URLs

Jira:
- `https://api.example.com/api/v1/integrations/jira/callback`

Slack:
- `https://api.example.com/api/v1/integrations/slack/callback`

## Smoke Checks

```bash
curl https://api.example.com/healthz
curl https://api.example.com/api/v1/integrations/status
curl https://api.example.com/api/v1/impact/links
```

## Platform References

- Railway Dockerfile deployments: https://docs.railway.com/guides/dockerfiles
- Fly.io app configuration: https://fly.io/docs/reference/configuration/
- Vercel project configuration: https://vercel.com/docs/project-configuration
- Chrome Web Store publishing: https://developer.chrome.com/docs/webstore/publish
