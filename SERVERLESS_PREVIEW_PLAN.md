# Serverless preview deployment evaluation (not deployed)

## What is optimized today
Identical queued, running or completed preview requests now reuse one durable job ID (24-hour retention). This reduces duplicate model fits and quota consumption. It does not precompute league parameters or make first-time predictions faster. Real latency benchmarks remain necessary.

## Reuse implementation (2026-11-02)
The single-worker queue now passes a process-local fitted-model cache to the collector. Models are keyed by league, UTC training cutoff date and Git revision. This avoids repeated fitting for different verified fixtures in the same league on the same worker and day. It does not survive restarts, prewarm a cold instance, or share state across replicas. Actual latency improvement has not yet been measured. Persistent precomputed artifacts are now implemented as an opt-in local disk cache using MATCHLAB_FITTED_SNAPSHOT_DIR. Every load re-fetches historical training data and checks its SHA256 digest, UTC cutoff and code version. This saves model fitting on a warm disk but not history downloading; it is not yet benchmarked against real fixtures.

## Cloud Run feasibility
The current Dockerfile.preview is a long-running HTTP service with a background worker and local SQLite database. It cannot be moved unchanged to scale-to-zero Cloud Run safely: CPU may be throttled after requests, local disk is ephemeral, and multiple replicas cannot share SQLite.

A proper serverless design would use a request service plus a durable job queue, a separate bounded worker job, and shared persistent result storage. Set max instances, concurrency, timeout, and authentication explicitly. Use the hosting provider's official pricing calculator and quotas before enabling billing. Do not embed football provider or service secrets in GitHub or client JavaScript.

## Release gates
1. Benchmark model fitting by league, cold start and repeated requests.
2. Completed in code: versioned fitted-model JSON artifacts with training dataset SHA256, cutoff and code revision; numerical round-trip regression tests. Production performance and storage reliability still need verification.
3. Verify provider fixture identity, UTC kickoff and rate limits.
4. Provision durable shared queue and result storage, then implement idempotent retries and timeout handling.
5. Run staging fixture tests and verify no writes to the official append-only archive.
6. Require explicit account/billing approval before any cloud resource is created.

## Cost decision
Keep scheduled archive forecasts on existing GitHub Actions and Vercel while serverless suitability is evaluated. This repository file alone creates no billable infrastructure.
