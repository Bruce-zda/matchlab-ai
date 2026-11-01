# Streamlit retirement audit (2026-11-01)

## Verified separation
- Public Next.js site lives under `frontend/` and loads archived JSON feeds directly from the repository.
- Forecast collector imports `football_models.py`, not `app.py` or Streamlit.
- The quality suite asserts that the standalone model module has no Streamlit import and that collector functions resolve to standalone models.
- Existing `app.py` remains a Streamlit application; root `requirements.txt` still includes Streamlit.
- The scheduled forecast, settlement, and integrity workflows run Python scripts, not the Streamlit UI.

## Retirement decision
**Safe to stop linking to Streamlit from the new site. Not yet safe to delete `app.py` or the root requirements.** Historical scripts or users may still rely on them; deleting now would remove a working fallback without proving parity.

## Completion checklist
1. Verify every production workflow uses standalone modules (including auxiliary audit/calibration workflows).
2. Confirm Vercel production deployment and archived feed availability independently.
3. Check remaining scripts for `app.py` imports and Streamlit-specific configuration.
4. Document any legacy features not yet represented on Next.js.
5. After parity and deployment checks, retire the hosted Streamlit service, then remove unused dependencies in a separately reviewed change.

The forecast archive must remain append-only throughout migration.

## Additional audit findings
- Historical model comparison formerly extracted functions from `app.py` using AST. It now imports standalone `football_models.py` directly, with a regression guard.
- Historical calibration (`scripts/calibration_report.py`) **still extracts eight functions from `app.py` using AST**. It is not yet independent and must be migrated carefully with parity tests before deleting the legacy app.
- `discover.py` is another Streamlit UI entry point; preserve it until retirement is authorized.
- Workflow triggers for model comparison and calibration no longer react to changes in the legacy `app.py`.

## 2026-11-01 calibration migration
- `historical_calibration.py` now owns the extracted exploratory rolling evaluation functions, imports standalone `football_models.py`, and has no Streamlit dependency.
- `scripts/calibration_report.py` calls this module directly, with a regression test preventing `app.py` AST extraction.
- Workflow report publication now retries on concurrent commits after a confirmed non-fast-forward push failure.
- Pending: full calibration workflow completion and independent parity review; do not retire `app.py` or `discover.py` yet.

## Verified CI evidence (2026-11-01)
- Standalone historical model comparison succeeded on five leagues and 5,190 paired fixtures; historical exploratory evaluation, not untouched proof.
- Standalone historical calibration succeeded on 15 folds with no data-source errors. Calibration gates remain closed and live calibration disabled.
- Calibration publishing conflict was fixed by rebuilding the generated report commit atop current `main`; workflow run 41338234157 succeeded.
- Vercel public URL was not independently reachable through the available read-only web check; do not claim a verified production deployment from a GitHub build alone.
- Streamlit entry points `app.py` and `discover.py` remain for a separate decommission decision; do not delete until hosting ownership and parity are verified.

## Production smoke result (2026-11-01)
- Public homepage returned HTTP 200 in two GitHub Actions checks.
- New `/api/health` route returned HTTP 404 on the public Vercel URL in both checks, despite a successful Next.js build. This is a **deployment parity blocker**, not proof of an archive-data failure.
- Production smoke workflow fails loudly until the route is deployed. Investigate Vercel project root directory (`frontend`), connected repository/branch, deployment status, and production domain alias; do not weaken the check or delete legacy hosting before resolution.

## Verified production recovery (2026-11-01)
- User independently opened the production `/api/health` URL and captured `status: ok`, `source: verified-repository-archive`, `archived_forecasts: 208`, `settled_forecasts: 28` at 2026-11-01T19:47:56.572Z.
- Vercel dashboard showed `main` deployments Ready, Next.js framework and `frontend` root, and the deployed `/api/health` function in Resources.
- Earlier smoke failures were recorded before the healthy endpoint was observed; consistent with deployment propagation, but the precise cause is not proven.
- Automated smoke workflow retry window increased to tolerate delayed propagation. A fresh passing CI run is still required before marking automated production monitoring green.
- Streamlit deletion remains deferred until legacy feature parity and hosting ownership are confirmed; do not modify immutable forward forecast archives.

## Feature-level parity audit (2026-11-01)

| Legacy Streamlit capability | Next.js status | Retirement gate |
| --- | --- | --- |
| Archived forecast discovery and league browsing (`discover.py`) | Present on homepage | Verify filtering and archive freshness before retirement |
| Archived per-match probability/model comparison | Present at `/match/[id]` | Verify representative fixtures and missing-market behavior |
| Settled forward model performance | Present at `/performance` | Preserve snapshot-level audit and sample-size warnings |
| Model descriptions and transparency | Present at `/methodology` | Keep methodology current |
| Manual home/away team selection and on-demand model analysis (`app.py`, Manual matchup tab) | **Not implemented as interactive Next.js feature** | Feature parity blocker |
| Current market odds loading and market-by-market evaluation (`app.py`) | **Not implemented as interactive Next.js feature** | Feature parity blocker; requires secured provider credentials |
| Historical test, five-league cross-league evaluation, rolling-origin validation and CSV exports (`app.py`) | Standalone CI artifacts exist, but **not equivalent interactive Next.js UI/exports** | Feature parity blocker if user-facing analysis must remain |
| Asian handicap side controls (`app.py`) | Not verified on Next.js | Audit market-specific parity before removal |
| Discover competition and Upcoming/All archived/Completed filters (`discover.py`) | League browsing present; complete filter parity not established | Verify period filtering |

### CI confirmation
- Production smoke check run 41344124063 **success** after retry-window adjustment.
- Historical calibration run 41344138847 **success** after standalone module added to trigger paths.
- Quality runs 41344154426, 41344138839 and 41344124034 **success**.

### Decision
**Do not delete `app.py`, `discover.py`, or Streamlit dependencies yet.** The Next.js public site is healthy, but legacy feature parity is incomplete. Retirement can proceed only after choosing which legacy interactive tools to rebuild versus explicitly discontinue, and confirming any remaining Streamlit hosting dependencies. This is distinct from safely keeping Next.js as the sole advertised public site.

## Manual matchup migration progress
- Next.js `/manual` archived matchup explorer is implemented and its full frontend build passed (GitHub Actions 41346189459); this is archive browsing, **not** arbitrary on-demand forecasting.
- `scripts/manual_preview.py` adds an independent CLI for freshly fitted four-model previews using the production collector, with explicit future UTC kickoff, validated league/team inputs, isolated empty ledger, and `official_forward_archive: false` output. Supplied fixtures are explicitly **not independently verified**.
- `tests/test_manual_preview.py` guards preview validation and non-publication. This CLI is **not** yet a website feature; exposing it requires a secure compute backend, rate limiting, independent fixture verification and resource controls. Never run scipy model fitting inside a standard Next.js route without a designed runtime.
