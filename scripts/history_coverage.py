"""Audit OpenFootball season coverage without changing prediction inputs.

Run: python scripts/history_coverage.py
"""
import datetime as dt
import json
import pathlib
import sys
import time
import requests

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from data_quality import valid_score_pair, valid_team_pair

LEAGUES = {'Premier League':'en.1','La Liga':'es.1','Serie A':'it.1',
           'Bundesliga':'de.1','Ligue 1':'fr.1'}


def audit_season(session, season, code):
    url = f'https://raw.githubusercontent.com/openfootball/football.json/master/{season}/{code}.json'
    try:
        response = session.get(url, timeout=15)
        response.raise_for_status()
        payload = response.json()
        games = payload.get('matches') or [
            m for r in payload.get('rounds', []) for m in r.get('matches', [])]
        valid = 0
        seen = set()
        for match in games:
            home, away = match.get('team1'), match.get('team2')
            def name(value):
                return value.get('name', value.get('key', '')) if isinstance(value, dict) else value
            home, away = name(home), name(away)
            score = match.get('score')
            ft = score.get('ft') if isinstance(score, dict) else score
            if isinstance(ft, dict):
                ft = [ft.get('home'), ft.get('away')]
            if not isinstance(ft, list) or len(ft) < 2:
                continue
            date = match.get('date')
            try:
                match_date = dt.date.fromisoformat(str(date)[:10])
            except (TypeError, ValueError):
                continue
            key = (match_date, home, away)
            if (match_date > dt.date.today() or key in seen
                    or not valid_team_pair(home, away)
                    or not valid_score_pair(ft[0], ft[1])):
                continue
            seen.add(key)
            valid += 1
        return {'season': season, 'status': 'ok' if valid else 'empty',
                'valid_completed_matches': valid}
    except (requests.RequestException, ValueError, TypeError, KeyError) as exc:
        return {'season': season, 'status': 'unavailable',
                'valid_completed_matches': 0, 'error': type(exc).__name__}


def main():
    year = dt.date.today().year if dt.date.today().month >= 7 else dt.date.today().year - 1
    result = {'generated_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
              'scope': 'OpenFootball archive coverage; not model accuracy',
              'leagues': {}}
    with requests.Session() as session:
        for league, code in LEAGUES.items():
            seasons = []
            for y in range(year - 7, year + 1):
                seasons.append(audit_season(session, f'{y}-{str(y+1)[-2:]}', code))
                time.sleep(.1)
            result['leagues'][league] = {
                'seasons': seasons,
                'available_seasons': sum(s['status'] == 'ok' for s in seasons),
                'completed_matches': sum(s['valid_completed_matches'] for s in seasons),
            }
    output = ROOT / 'artifacts'
    output.mkdir(exist_ok=True)
    (output / 'history_coverage.json').write_text(json.dumps(result, indent=2) + '\n')
    for league, details in result['leagues'].items():
        print(f"{league}: {details['available_seasons']}/8 seasons; {details['completed_matches']} matches")
    if not any(item['available_seasons'] for item in result['leagues'].values()):
        raise SystemExit('No historical league coverage: audit failed')


if __name__ == '__main__':
    main()
