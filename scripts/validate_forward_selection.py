"""Read official append-only forward evidence; write research report outside official archive."""
import json
import pathlib
import sys
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from forward_selection_validation import evaluate_forward_screen

def main():
    ledger=json.loads((ROOT/"artifacts"/"forward_ledger.json").read_text())
    settlements=json.loads((ROOT/"artifacts"/"forward_settlements.json").read_text())
    report=evaluate_forward_screen(ledger,settlements)
    output=ROOT/"reports"/"forward_selection_validation.json"
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps(report,indent=2,allow_nan=False)+"\n")
    print(json.dumps(report,indent=2))

if __name__=="__main__":
    main()
