"""football-data.org v4 adapter. Never imports or reads bookmaker odds."""
import datetime as dt
import requests
from forward_validation import utc_time

CODES={'PL':'Premier League','PD':'La Liga','SA':'Serie A',
       'BL1':'Bundesliga','FL1':'Ligue 1'}
API='https://api.football-data.org/v4'

def get_matches(token, date_from, date_to):
    if not token:
        raise ValueError('FOOTBALL_DATA_TOKEN is required')
    if date_from>date_to:
        raise ValueError('Invalid date range')
    response=requests.get(API+'/matches',headers={'X-Auth-Token':token},
        params={'competitions':','.join(CODES),'dateFrom':date_from,'dateTo':date_to},
        timeout=25)
    response.raise_for_status()
    payload=response.json()
    if not isinstance(payload.get('matches'),list):
        raise ValueError('Unexpected match API response')
    return payload['matches']

def upcoming_fixtures(matches, now):
    now=utc_time(now)
    fixtures=[]
    for match in matches:
        competition=match.get('competition') or {}
        code=competition.get('code')
        if code not in CODES or match.get('status') not in ('SCHEDULED','TIMED'):
            continue
        home=(match.get('homeTeam') or {}).get('name')
        away=(match.get('awayTeam') or {}).get('name')
        kickoff=match.get('utcDate')
        match_id=match.get('id')
        if not isinstance(home,str) or not isinstance(away,str) or not isinstance(match_id,int):
            continue
        try:
            timestamp=utc_time(kickoff)
        except (TypeError,ValueError):
            continue
        if timestamp<=now or timestamp>now+dt.timedelta(days=7):
            continue
        fixtures.append({'league':CODES[code],'home':home,'away':away,
                         'kickoff_utc':timestamp.isoformat(),'provider_match_id':match_id})
    return fixtures

def finished_scores(matches):
    scores=[]
    for match in matches:
        if match.get('status')!='FINISHED':
            continue
        full=((match.get('score') or {}).get('fullTime') or {})
        home,away=full.get('home'),full.get('away')
        if not all(isinstance(g,int) and not isinstance(g,bool) and g>=0 for g in (home,away)):
            continue
        scores.append({'provider_match_id':match.get('id'),'home_goals':home,'away_goals':away})
    return scores
