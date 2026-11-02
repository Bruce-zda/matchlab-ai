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
    # Multiple model settlements may reference the same fixture. Accept identical
    # scores once; reject any conflict rather than silently choosing a result.
    unique_finals={}
    for r in settlements:
        fid=r.get("provider_match_id")
        h,a=r.get("home_goals"),r.get("away_goals")
        if fid is None or type(h) is not int or type(a) is not int or h<0 or a<0:
            continue
        key=str(fid)
        score=(h,a)
        if key in unique_finals and unique_finals[key]!=score:
            raise ValueError("Conflicting final scores for fixture "+key)
        unique_finals[key]=score
    finals=[{"provider_match_id":key,"status":"final","home_goals":score[0],
             "away_goals":score[1]} for key,score in unique_finals.items()]
    report=evaluate_live_screen(eligible,finals)
    report["unique_final_fixtures"]=len(unique_finals)
    report["legacy_hybrid_snapshots_excluded"]=excluded
    report["note"]="Existing historical snapshots cannot be retrospectively assigned screen decisions."
    output=ROOT/"reports/forward_live_screen_validation.json"
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report,indent=2,allow_nan=False)+"\n")
    print(json.dumps(report,indent=2,allow_nan=False))

if __name__=="__main__":
    main()
