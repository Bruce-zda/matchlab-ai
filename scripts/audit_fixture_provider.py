"""Scheduled provider connectivity audit; no predictions are published."""
import datetime as dt
import json
import os
import pathlib
import sys
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from football_data_provider import get_matches,upcoming_fixtures,finished_scores

def main():
    token=os.environ.get('FOOTBALL_DATA_TOKEN','')
    if not token:
        raise SystemExit('Missing FOOTBALL_DATA_TOKEN GitHub Actions secret')
    now=dt.datetime.now(dt.timezone.utc)
    start=now.date().isoformat()
    end=(now+dt.timedelta(days=7)).date().isoformat()
    matches=get_matches(token,start,end)
    fixtures=upcoming_fixtures(matches,now.isoformat())
    scores=finished_scores(matches)
    out=ROOT/'artifacts'
    out.mkdir(exist_ok=True)
    (out/'provider_fixture_audit.json').write_text(json.dumps({
        'checked_at_utc':now.isoformat(),'source':'football-data.org',
        'matches_returned':len(matches),'upcoming_fixtures':len(fixtures),
        'finished_matches':len(scores),'fixtures':fixtures,
        'status':'connectivity_only_no_forward_forecasts_published'},indent=2)+'\n')
    print(f'Provider audit: {len(matches)} matches, {len(fixtures)} upcoming fixtures, {len(scores)} finished')
    if not matches:
        raise SystemExit('Provider returned no matches in the window')

if __name__=='__main__':
    main()
