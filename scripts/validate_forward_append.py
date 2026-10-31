"""Validate candidate forward ledger is an append-only extension of the published ledger."""
import json
import pathlib
import sys
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from forward_validation import snapshot_id,validate_forecast

def check(old,new):
    if not isinstance(old,list) or not isinstance(new,list):
        raise ValueError('Ledgers must be arrays')
    if len(new)<len(old) or new[:len(old)]!=old:
        raise ValueError('Candidate changes or removes previously published forecasts')
    identities=set()
    for entry in new:
        validate_forecast(entry)
        identity=snapshot_id(entry)
        if entry.get('snapshot_id')!=identity or identity in identities:
            raise ValueError('Missing, incorrect, or duplicated snapshot identity')
        identities.add(identity)
    return len(new)-len(old)

def main():
    if len(sys.argv)!=3:
        raise SystemExit('Usage: python scripts/validate_forward_append.py existing.json candidate.json')
    old_path,new_path=map(pathlib.Path,sys.argv[1:])
    old=json.loads(old_path.read_text()) if old_path.exists() else []
    new=json.loads(new_path.read_text())
    added=check(old,new)
    print(f'Append-only validation passed: {len(old)} retained, {added} new')
    return added

if __name__=='__main__':
    main()
