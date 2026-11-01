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
