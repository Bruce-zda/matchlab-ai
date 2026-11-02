"""Evaluate newly captured frozen live-screen picks without altering archives."""
import json
import pathlib
import sys
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from forward_live_screen_validation import evaluate_live_screen

def main():
    ledger=json.loads((ROOT/"artifacts/forward_ledger.json").read_text())
    settlements=json.loads((ROOT/"artifacts/forward_settlements.json").read_text())
    hybrid=[r for r in ledger if r.get("model")=="DC + Bayesian (50/50)"]
    eligible=[r for r in hybrid if isinstance(r.get("screen_markets"),list)]
    excluded=len(hybrid)-len(eligible)
    finals=[{**r,"status":"final"} for r in settlements if
            r.get("provider_match_id") is not None and
            isinstance(r.get("home_goals"),int) and isinstance(r.get("away_goals"),int)]
    report=evaluate_live_screen(eligible,finals)
    report["legacy_hybrid_snapshots_excluded"]=excluded
    report["note"]="Existing historical snapshots cannot be retrospectively assigned screen decisions."
    output=ROOT/"reports/forward_live_screen_validation.json"
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report,indent=2,allow_nan=False)+"\n")
    print(json.dumps(report,indent=2,allow_nan=False))

if __name__=="__main__":
    main()
