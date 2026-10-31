# MatchLab — release roadmap

Last updated: 2026-10-31

Legend: [x] implemented and user-verified at prototype level; [ ] outstanding; [~] in progress.

- [x] 1. Build Dixon–Coles prediction engine.
- [x] 2. Integrate five European leagues and fixture feeds.
- [x] 3. Add match analysis and multiple prediction markets.
- [x] 4. Implement historical, cross-league and rolling backtests.
- [x] 5. Compare forecasts against league-frequency and club-specific baselines.
- [~] 6. Validate priority markets (Double Chance and Asian Handicap) and improve probability calibration. Acceptance: training-only calibration, rolling tests against relevant baselines, and independent untouched evaluation; goals-market experiments remain deferred.
- [ ] 7. Validate expert-pick policy. Acceptance: independent per-market performance, sufficient sample sizes, honest abstention; no claims of guaranteed accuracy.
- [ ] 8. Deliver premium mobile-first UI. Acceptance: legible on typical phone without desktop zoom, consistent navigation, polished match centre.
- [ ] 9. Harden data and deployment. Acceptance: duplicate checks, freshness notices, unavailable-feed fallback, automated smoke tests, dependency pinning, source/license compliance.
- [ ] 10. Final QA and release. Acceptance: app loads, five leagues work, fixture and manual forecasts work, backtests complete, mobile QA and published URL verified.

## Evidence so far
- Historical holdout: five leagues, 495 matches evaluated, MatchLab beat the league-frequency baseline in each league.
- Rolling validation: 15 historical folds, 14 beat league-frequency baseline, 11 beat smoothed club-specific baseline. Folds can be correlated; these are exploratory findings, not independent proof of future performance.
- Goal markets and BTTS have mixed results. Expert picks remain withheld.
- Goal-rate shrinkage challenger improved current goal Brier in 14/15 rolling folds, but beat league goal-frequency baseline in only 7/15 folds.
- Independent venue-based goals benchmark improved current goal Brier in 9/15 folds and beat league goal-frequency baseline in 7/15 folds.
- Decision: do not promote either goal challenger. Keep goals markets explicitly exploratory; postpone further goal-model tuning until genuinely new evaluation data are available.
- Milestone 6 remains open: the required independently validated calibration improvement has not been demonstrated. UI/release engineering can proceed in parallel.
- No live odds, injury/lineup feed, independent final holdout, or demonstrated betting value.

## Release rules
- Do not mark a milestone complete merely because code was committed.
- Keep predictions and their limitations clearly labeled.
- Do not silently select a favorable test set or tune on the final evaluation set.
- Preserve attribution and respect upstream noncommercial licensing.

## Priority-market test (2026-10-31)
- User-verified rolling results: Double Chance 1X and X2 beat club-specific baseline in 13/15 folds; 12 in 10/15.
- Asian Handicap settlement MSE beats historical goal-difference baseline in 14–15/15 folds across tested lines from -1.0 to +1.0.
- These are correlated development folds, not independent final validation; no odds or ROI tested. Do not label selections expert-validated or profitable.
- Product focus: Double Chance and Asian Handicap; goal markets secondary; corners deferred until verified data exists.
