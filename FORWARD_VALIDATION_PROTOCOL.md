# MatchLab forward-validation protocol — frozen initial specification

Status: **collection not yet active**. No forward-validated performance claims are permitted until actual pre-kickoff snapshots and independently verified final scores exist.

## Candidate models
- Incumbent: Dixon–Coles.
- Challenger: 50/50 arithmetic probability blend of Dixon–Coles and Bayesian Goals.
- Diagnostic comparators: Bayesian Goals and Elo.
- No bookmaker prices enter the probability engines or scoring.

## Pre-registration
- Archive the model source commit SHA, parameter settings, training-data cutoff, fixture identity, scheduled kickoff UTC, capture UTC, and 1X2 probabilities.
- Record every eligible fixture before kickoff. Never backfill, edit, or silently delete an earlier forecast.
- Freeze model code and blend weight for the evaluation cohort. Code changes create a **new cohort**, not retroactive changes to existing snapshots.
- Match forecasts to final scores using independently checked fixture identities and verified kickoff times. Postponements, abandoned games, duplicate fixtures and uncertain identities must be explicitly flagged, not silently scored.
- Track all eligible fixtures, skipped forecasts, and reasons for exclusions. Report coverage and data-source freshness.

## Primary evaluation
- Primary metric: multiclass 1X2 Brier score, using the mean of three squared outcome errors.
- Secondary metric: 1X2 log loss.
- Compare models on identical settled fixtures using paired differences.
- Include league-level metrics and temporal block-bootstrap uncertainty intervals.
- Show raw prediction counts, missingness, and any fixture-data corrections.
- Calibration diagnostics are descriptive and do not constitute independent calibration validation.

## Promotion gate (conservative, prospective)
- Do not promote before at least 1,000 **new, timestamped, settled** paired fixtures across the five leagues, with at least 100 per league and coverage >= 90% of independently identified eligible fixtures.
- Require challenger to improve the primary Brier score and secondary log loss, with paired 95% temporal-block bootstrap intervals entirely below zero on both metrics.
- Require no material deterioration in any league; investigate all league-level regressions.
- Any change to these criteria before evaluation completes must be disclosed as a protocol revision, not hidden.
- No guarantee of profitability or match-by-match accuracy is implied.

## Current state
The historical 5,190-fixture results are exploratory and do **not** count toward the forward-testing sample. The ledger validation module is available, but an independent scheduled pre-kickoff collector and result-settlement process must still be deployed and verified before the forward-test clock starts.
