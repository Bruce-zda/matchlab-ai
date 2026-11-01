# MatchLab no-additional-hosting-cost rollout

## Architecture
- Vercel hosts the Next.js site, subject to plan limits.
- GitHub Actions runs scheduled pilot forecasts at 05:05, 11:05 and 17:05 UTC, dependent on provider credentials, quotas and workflow reliability.
- The append-only forward archive and integrity manifest remain unchanged.
- The matchup explorer filters archived forecasts by league, teams, orientation and kickoff status.
- On-demand compute remains disabled until securely deployed. The optional paid Render Blueprint is not activated.

## Release checks
1. Verify scheduled forecasts and settlement workflows are green and actually refreshing.
2. Verify deployed /manual filters after Vercel deploys the latest main commit.
3. Monitor GitHub Actions minutes, provider quotas and Vercel plan limits. No additional hosting cost is not a guarantee of zero future charges.
4. Never fabricate missing fixtures or retroactively publish predictions.
5. Do not claim validated profitability or on-demand availability.

## Deferred
- Arbitrary on-demand prediction generation.
- Live odds and full market-by-market analysis.
- Full Streamlit parity and retirement.
