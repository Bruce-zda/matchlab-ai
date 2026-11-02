"""Evaluate previously generated historical market forecasts; never train on results."""
import json
import pathlib
import sys
import pandas as pd
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from historical_market_validation import evaluate_historical_markets

def main():
    path=ROOT/"artifacts"/"historical_market_predictions.csv"
    if not path.exists():
        raise SystemExit("Missing chronological market predictions; run scripts/model_comparison.py first")
    data=pd.read_csv(path)
    report=evaluate_historical_markets(data.to_dict("records"))
    out=ROOT/"reports"/"historical_market_validation.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(report,indent=2,allow_nan=False)+"\n")
    print(json.dumps({k:v for k,v in report.items() if k!="markets"},indent=2))

if __name__=="__main__":
    main()
