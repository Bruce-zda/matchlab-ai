# MatchLab AI — Active delivery roadmap (2026-11-01)

## Product principle
One Next.js/Vercel public website, a standalone Python forecast engine, immutable pre-kickoff predictions, independent evaluation, and no fabricated confidence or betting-value claims.

## Completed / committed
- Five-league fixture collection, Dixon–Coles, Bayesian Goals, Elo and experimental 50/50 hybrid.
- Standalone `football_models.py`; collector no longer extracts model functions from Streamlit `app.py`.
- Official append-only forecast ledger, integrity checks, automated settlement and historical evaluation tooling.
- Score-grid goal markets (BTTS, totals, team totals, correct scores) for new eligible forecasts.
- Isolated preview workflow: `.github/workflows/forward-dry-run.yml`; preview data is not published to the official ledger.
- Vercel Discover and Match Centre.
- Native Vercel Performance Lab (`/performance`) with real settlement metrics and small-sample warning.
- Public Methodology page (`/methodology`).
- Standalone engine regression tests and expanded Python syntax checks.

## Immediate work — no fixture waiting required
- [ ] Confirm current frontend build and Python quality checks on the latest commit.
- [ ] Audit remaining Streamlit dependencies and remove production-only coupling; retire old hosted deployment after verification.
- [ ] Verify preview workflow end-to-end with a real fixture feed; make preview results accessible in Vercel without publishing them as official.
- [ ] Add strict tests for goal-market math, forecast schema, source freshness, fixture deduplication, and settlement correctness.
- [ ] Implement market-specific performance scoring for BTTS, totals, and team goals when actual archived market probabilities exist.
- [ ] Expand Performance Lab with league filters, calibration visualization, sample-size thresholds, and downloadable verified results.
- [ ] Improve Match Centre with real team-form stats, model disagreement details, and explicit missing-data states.
- [ ] Add search, sorting, and better filtering to Discover; verify keyboard and mobile behavior.
- [ ] Introduce monitoring and actionable pipeline failure notices.
- [ ] Evaluate source licenses, security, API credentials, dependency pins, caching and production recovery procedures.
- [ ] Introduce typed forecast-data contracts and plan a database/API migration without changing immutable archives.

## Evidence-dependent — cannot be fast-forwarded
- [ ] Capture new official goal-market forecasts before kickoff and settle against completed matches.
- [ ] Accumulate independent chronological evaluation results; 1,000 settled fixtures is an initial milestone, not automatic statistical proof.
- [ ] Validate per-market calibration and model selection on genuinely unseen matches.
- [ ] Avoid expert-pick or profitability claims until adequate independent evidence exists.

## Deferred scope
Accounts, subscriptions, live score providers, lineup/injury integrations, corners, cards, player markets, additional competitions, and public API are not launch prerequisites. Each needs independent source, licensing, cost and reliability assessment.

## Release gates
1. **Infrastructure:** all production paths Streamlit-independent; automated checks green.
2. **Markets:** authentic published pre-kickoff market snapshots; safe previews; market-level settlement.
3. **Analysis:** rich Match Centre and verified performance dashboards.
4. **Quality:** responsive, accessible UI; monitoring, privacy/security, license review.
5. **Public release:** no misleading evidence claims; transparent methodology and working recovery procedures.

## Operational caveat
GitHub Actions `workflow_dispatch` cannot be invoked through the current connected GitHub interface. The preview workflow can be edited and reviewed automatically, but an actual dispatch requires a compatible runner/connector or user action. Never claim it ran without a recorded run.
