"""Fetch recent results for saved pilot fixture IDs; no bookmaker data."""
import datetime as dt
import json
import os
import pathlib
import sys
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from football_data_provider import get_matches

def main():
    ledger_path=ROOT/'artifacts'/'forward_ledger.json'
    ledger=json.loads(ledger_path.read_text()) if ledger_path.exists() else []
    if not ledger:
        print('No published forecasts to settle')
        (ROOT/'artifacts'/'forward_provider_matches.json').write_text('[]\n')
        return
    token=os.environ.get('FOOTBALL_DATA_TOKEN','')
    if not token:
        raise SystemExit('Missing FOOTBALL_DATA_TOKEN')
    now=dt.datetime.now(dt.timezone.utc)
    # Query all dates from the oldest recorded fixture through today,
    # capped at 30 days per request to keep API responses manageable.
    earliest=min(dt.datetime.fromisoformat(r['kickoff_utc']).date() for r in ledger)
    last=now.date()
    if earliest>last:
        matches=[]
    else:
        matches=[]
        day=earliest
        while day<=last:
            end=min(day+dt.timedelta(days=29),last)
            matches.extend(get_matches(token,day.isoformat(),end.isoformat()))
            day=end+dt.timedelta(days=1)
    ids={r.get('provider_match_id') for r in ledger}
    selected=[m for m in matches if m.get('id') in ids]
    (ROOT/'artifacts'/'forward_provider_matches.json').write_text(json.dumps(selected,indent=2)+'\n')
    print(f'Fetched {len(selected)} matching provider fixtures from {len(matches)} source records')

if __name__=='__main__':
    main()
