# MatchLab private preview compute deployment

The Python preview service is intentionally **not deployed automatically**. It requires an isolated HTTPS hosting service and two secrets; neither secret belongs in Git.

## Deployment requirements

1. Deploy this repository as a **separate Python service** with a **single worker**, 2 GB+ memory and a bounded request/runtime timeout. Startup: `python preview_service.py`. Install `numpy>=1.24,<3`, `scipy>=1.11,<2`, `pandas>=2,<3`, `requests>=2.31,<3`. Restrict network ingress to the Next.js service where supported.
2. Set `MATCHLAB_PREVIEW_SERVICE_TOKEN` to a long random secret (service only), and `FOOTBALL_DATA_TOKEN` to the authorized football-data.org v4 API token (service only).
3. Set Vercel's `MATCHLAB_PREVIEW_BACKEND_URL` to the exact HTTPS endpoint ending in `/preview`; set Vercel's `MATCHLAB_PREVIEW_BACKEND_TOKEN` to the same random secret. Never use `NEXT_PUBLIC_` for secrets.
4. Verify `GET /health` is healthy on the Python service, then exercise a verified upcoming fixture with a real provider name and UTC kickoff through the website.
5. Ensure hosting-level persistent distributed rate limiting, cost quotas, authentication, observability and alerting before opening the endpoint to significant public traffic. In-memory limits are **not sufficient** for multiple replicas, restarts, or production abuse resistance.
6. Keep official `artifacts/forward_ledger.json` and settlements immutable. Previews are generated live and never published as archived forecasts.

## Failure modes and limitations

- The UI is deliberately hidden when either Vercel preview environment variable is missing.
- Provider verification must match **exact league, home team, away team, and kickoff** before fitting. The user-selected team names are sourced from the archived ledger and might not cover all current fixtures.
- The preview service currently fetches and fits up to eight historical seasons per request; this can be slow and costly. Use an authenticated, queued, cached model worker with persistent throttling for production scale.
- The provider may reject requests or rate limit; the service fails closed.
- The Next.js proxy times out after 25 seconds. If historical fitting takes longer, use an asynchronous job API rather than increasing a serverless request timeout indefinitely.
- This implementation does not establish predictive accuracy or profitability. No live calibration is enabled.

## Deployment gate

**Do not claim public on-demand predictions are live until the private service is deployed, environment variables are configured, a real end-to-end verified fixture test passes, and distributed rate limiting is operational.**
