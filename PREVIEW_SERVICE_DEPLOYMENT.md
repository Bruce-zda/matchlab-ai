# MatchLab private preview compute deployment

The Python preview service is intentionally **not deployed automatically**. It requires an isolated HTTPS hosting service and two secrets; neither secret belongs in Git.

## Deployment requirements

1. Deploy this repository as a **separate Python service** with a **single worker**, 2 GB+ memory and a bounded request/runtime timeout. Startup: `python preview_service.py`. Install `numpy>=1.24,<3`, `scipy>=1.11,<2`, `pandas>=2,<3`, `requests>=2.31,<3`. Restrict network ingress to the Next.js service where supported.
2. Set `MATCHLAB_PREVIEW_SERVICE_TOKEN` to a long random secret (service only), and `FOOTBALL_DATA_TOKEN` to the authorized football-data.org v4 API token (service only).
3. Set Vercel's `MATCHLAB_PREVIEW_BACKEND_URL` to the exact HTTPS endpoint ending in `/jobs`; set Vercel's `MATCHLAB_PREVIEW_BACKEND_TOKEN` to the same random secret. Never use `NEXT_PUBLIC_` for secrets.
4. Verify `GET /health` is healthy on the Python service, then exercise a verified upcoming fixture with a real provider name and UTC kickoff through the website.
5. Ensure hosting-level persistent distributed rate limiting, cost quotas, authentication, observability and alerting before opening the endpoint to significant public traffic. SQLite quotas persist on the mounted volume, but this single-process design is **not** safe for multiple replicas or high-volume public abuse.
6. Keep official `artifacts/forward_ledger.json` and settlements immutable. Previews are generated live and never published as archived forecasts.

## Failure modes and limitations

- The UI is deliberately hidden when either Vercel preview environment variable is missing.
- Provider verification must match **exact league, home team, away team, and kickoff** before fitting. The user-selected team names are sourced from the archived ledger and might not cover all current fixtures.
- The preview service currently fetches and fits up to eight historical seasons per request; this can be slow and costly. Use an authenticated, queued, cached model worker with persistent throttling for production scale.
- The provider may reject requests or rate limit; the service fails closed.
- The Next.js proxy submits jobs asynchronously and polls for results. Fitting may exceed the browser's current three-minute polling window; job resume is not yet implemented.
- This implementation does not establish predictive accuracy or profitability. No live calibration is enabled.

## Deployment gate

**Do not claim public on-demand predictions are live until the private service is deployed, environment variables are configured, a real end-to-end verified fixture test passes, and distributed rate limiting is operational.**

## Async job architecture (2026-11-01)

The backend now exposes authenticated `POST /jobs` (returns HTTP 202 and opaque job ID) and `GET /jobs/{id}` (queued/running/complete/failed). Next.js proxies these through `POST /api/manual-preview` and `GET /api/manual-preview?job_id=...`. The browser polls while a single background worker verifies the provider fixture and fits models.

**Important deployment changes:** Set `MATCHLAB_PREVIEW_BACKEND_URL` to the exact HTTPS endpoint ending in **`/jobs`** (not `/preview`). Set `MATCHLAB_PREVIEW_DB` to a file on a **persistent mounted volume**. Deploy **exactly one process/replica**; the in-process worker and SQLite quota database are not a distributed multi-replica architecture. Persistent quotas survive process restarts only if the mounted volume persists. Jobs in the running state are requeued after restart. Finished jobs and identifiers expire after 24 hours. A job ID is a bearer capability: keep it private.

The public site remains disabled until hosting, secrets and full integration testing are complete. For production at scale, replace this single-worker architecture with a managed durable queue, central quota enforcement, monitoring and a shared data store. The browser currently polls for up to three minutes; jobs may need longer and should support resume by ID in a later iteration.

## Container and staging test

Build with `docker build -f Dockerfile.preview -t matchlab-preview .`. Run with a **writable, persistent** volume mounted at `/data` and `MATCHLAB_PREVIEW_DB=/data/jobs.sqlite`, plus both private tokens. The image runs as UID 10001, so the volume must be writable by that UID. Expose the HTTP port through a hosting-managed HTTPS reverse proxy; never publish the Python service without TLS. Only deploy one replica. The service refuses to start without a configured persistent database path.

CI runs `tests/test_preview_integration.py`: a real local HTTP server, authenticated submission, durable queue, mocked provider/model computation, and job polling. **This is a mocked integration test, not proof of real provider availability or a successful external deployment.** Before enabling the site, test one verified upcoming match with live provider credentials and real model fitting, record latency and resource use, and configure upstream access controls and quotas.

Deployment is blocked until a hosting account, writable persistent volume, football-data.org token, and private service secret are available. No credentials should be committed or pasted into public issues.

## Opt-in Render deployment blueprint

A repository-root `render.yaml` defines a **paid**, single-instance Render Docker web service with a 5 GB persistent disk and auto-deploy disabled. This is configuration only; no Render service, disk, billable plan or secret has been created. Review expected costs before approving the Blueprint. See the official Render Blueprint specification and deployment guide.

1. In your own Render account, create a Blueprint connected to this repository's `main` branch. Review the `standard` plan and persistent-disk charges **before** confirming. The Blueprint prompts for `MATCHLAB_PREVIEW_SERVICE_TOKEN` and `FOOTBALL_DATA_TOKEN`; supply secrets in Render, never in GitHub files.
2. Confirm the mounted `/data` volume is writable by container UID 10001, or adjust volume ownership using the host's supported mechanism. The service refuses to start without writable persistent storage.
3. Verify the Render HTTPS service's `/health` endpoint, then set Vercel's `MATCHLAB_PREVIEW_BACKEND_URL` to `https://<your-host>/jobs` and `MATCHLAB_PREVIEW_BACKEND_TOKEN` to the **same** secret. Both variables must be server-side only.
4. Test a real provider-verified upcoming fixture, complete the queue lifecycle, measure compute latency, verify the immutable forward ledger did not change, and review cost/abuse protections before enabling public access.

**Security note:** A secret-bearing HTTPS service is not the same as a private network. Render's public web endpoint remains reachable; bearer authentication, persistent quotas, upstream traffic controls, monitoring, and credential rotation remain essential. The existing 3/hour quota is global to the service, not per-user, and can be exhausted by one client. The optional Blueprint intentionally does not activate the Vercel feature on its own.
