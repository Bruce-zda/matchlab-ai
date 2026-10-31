"""Pre-kickoff forecast collector, driven by a verified UTC kickoff fixture feed.

Usage: python scripts/collect_forward.py fixtures.json ledger.json
Fixture JSON is an array of {league,home,away,kickoff_utc}.
Date-only fixtures are rejected: we never invent kickoff times.
This script does not fetch a live schedule or publish forecasts on its own.
"""
import ast
import datetime as dt
import io
import json
import pathlib
import re
import sys
import numpy as np
import pandas as pd
import requests
from scipy.optimize import minimize
from scipy.stats import poisson

ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from forward_validation import append_snapshot,utc_time
from bayesian_goals import BayesianGoals
from elo_baseline import EloBaseline
from data_quality import valid_score_pair,valid_team_pair
from football_data_provider import get_matches,upcoming_fixtures
import os
import re

LEAGUES={'Premier League':'en.1','La Liga':'es.1','Serie A':'it.1',
         'Bundesliga':'de.1','Ligue 1':'fr.1'}

def models_from_app():
    tree=ast.parse((ROOT/'app.py').read_text(encoding='utf-8'))
    names={'fetch_season','fit_dc','forecast'}
    nodes=[]
    for node in tree.body:
        if isinstance(node,ast.FunctionDef) and node.name in names:
            node.decorator_list=[]
            nodes.append(node)
    if {n.name for n in nodes}!=names:
        raise RuntimeError('App model API changed')
    class WarningSink:
        @staticmethod
        def warning(message):
            print('MODEL WARNING:',message,file=sys.stderr)
    ns={'pd':pd,'np':np,'requests':requests,'poisson':poisson,
        'minimize':minimize,'st':WarningSink,'valid_team_pair':valid_team_pair,
        'valid_score_pair':valid_score_pair}
    exec(compile(ast.fix_missing_locations(ast.Module(body=nodes,type_ignores=[])),
                 str(ROOT/'app.py'),'exec'),ns)
    return ns

def canonical_name(name):
    return re.sub(r'[^a-z0-9]', '', str(name).casefold().replace('&','and'))

# Only approved normalization variants. No fuzzy or substring matching.
TEAM_ALIASES={
    'manutd':'manchesterunited',
    'manchesterunited':'manchesterunited',
    'mancity':'manchestercity',
    'manchestercity':'manchestercity',
    'spurs':'tottenhamhotspur',
    'tottenham':'tottenhamhotspur',
    'tottenhamhotspur':'tottenhamhotspur',
    'newcastle':'newcastleunited',
    'newcastleunited':'newcastleunited',
    'brighton':'brightonandhovealbion',
    'brightonandhovealbion':'brightonandhovealbion',
    'wolves':'wolverhamptonwanderers',
    'wolverhamptonwanderers':'wolverhamptonwanderers',
    'nottmforest':'nottinghamforest',
    'nottinghamforest':'nottinghamforest',
    'psg':'parissaintgermain',
    'parissaintgermain':'parissaintgermain',
    'inter':'internazionale',
    'internazionale':'internazionale',
    'bayern':'bayernmunchen',
    'bayernmunchen':'bayernmunchen',
}
def team_key(name):
    key=canonical_name(name)
    if key.endswith('fc'):
        key=key[:-2]
    return TEAM_ALIASES.get(key,key)

def match_team(provider_name,training_names):
    matches=[name for name in training_names if team_key(name)==team_key(provider_name)]
    if len(matches)!=1:
        raise ValueError('No unique approved team-name match: '+str(provider_name))
    return matches[0]

def collect(fixtures,ledger,now,model_version):
    now=utc_time(now)
    ns=models_from_app()
    output=list(ledger)
    audit=[]
    cache={}
    for fixture in fixtures:
        label={k:fixture.get(k) for k in ('league','home','away','kickoff_utc')}
        try:
            league=fixture['league']
            code=LEAGUES[league]
            kickoff=utc_time(fixture['kickoff_utc'])
            if not now<kickoff<=now+dt.timedelta(days=7):
                raise ValueError('Kickoff outside next seven days')
            if league not in cache:
                year=now.year if now.month>=7 else now.year-1
                frames=[]
                for y in range(year-7,year+1):
                    season=f'{y}-{str(y+1)[-2:]}'
                    try:
                        frame=ns['fetch_season'](season,code)
                        if not frame.empty:
                            frames.append(frame)
                    except (requests.RequestException,ValueError,KeyError,TypeError):
                        continue
                if not frames:
                    raise ValueError('No historical training data')
                history=pd.concat(frames,ignore_index=True)
                history=history.drop_duplicates(['Date','HomeTeam','AwayTeam'])
                history=history[history.Date.dt.date<now.date()].sort_values('Date')
                if len(history)<150:
                    raise ValueError('Insufficient historical training data')
                dc=ns['fit_dc'](history)
                bayes=BayesianGoals().fit(history)
                elo=EloBaseline()
                for match in history.itertuples():
                    elo.observe(match.HomeTeam,match.AwayTeam,match.FTHG,match.FTAG)
                cache[league]=(dc,bayes,elo)
            dc,bayes,elo=cache[league]
            home=match_team(fixture['home'],dc[0])
            away=match_team(fixture['away'],dc[0])
            if home not in dc[0] or away not in dc[0]:
                raise ValueError('Team names not matched to model training data')
            _,_,grid=ns['forecast'](dc,home,away)
            dc_p=np.array([np.tril(grid,-1).sum(),np.trace(grid),np.triu(grid,1).sum()])
            bayes_p=bayes.predict(home,away)
            elo_p=elo.predict(home,away)
            probabilities={'Dixon-Coles':dc_p,'Bayesian Goals':bayes_p,
                           'Elo':elo_p,'DC + Bayesian (50/50)':(dc_p+bayes_p)/2}
            for model,probs in probabilities.items():
                record={'league':league,'home':home,'away':away,
                        'kickoff_utc':kickoff.isoformat(),
                        'captured_at_utc':now.isoformat(),
                        'model':model,'model_version':model_version,
                        'provider_match_id':fixture.get('provider_match_id'),
                        'p_home':float(probs[0]),'p_draw':float(probs[1]),
                        'p_away':float(probs[2])}
                output=append_snapshot(output,record)
            audit.append({**label,'status':'recorded','models':len(probabilities)})
        except (KeyError,ValueError,TypeError,requests.RequestException) as exc:
            audit.append({**label,'status':'skipped','reason':str(exc)})
    return output,audit

def main():
    if len(sys.argv)!=3:
        raise SystemExit('Usage: python scripts/collect_forward.py fixtures.json|--provider ledger.json')
    ledger_path=pathlib.Path(sys.argv[2])
    if sys.argv[1]=='--provider':
        token=os.environ.get('FOOTBALL_DATA_TOKEN','')
        now=dt.datetime.now(dt.timezone.utc)
        matches=get_matches(token,now.date().isoformat(),(now+dt.timedelta(days=7)).date().isoformat())
        fixtures=upcoming_fixtures(matches,now.isoformat())
    else:
        fixtures=json.loads(pathlib.Path(sys.argv[1]).read_text())
    ledger=json.loads(ledger_path.read_text()) if ledger_path.exists() else []
    if not isinstance(fixtures,list) or not isinstance(ledger,list):
        raise SystemExit('Expected JSON arrays')
    version=__import__('subprocess').check_output(
        ['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    updated,audit=collect(fixtures,ledger,dt.datetime.now(dt.timezone.utc).isoformat(),version)
    # Never overwrite an existing ledger in place. Output a candidate append-only
    # ledger; a separate reviewed publishing process must preserve old snapshots.
    output=ledger_path.with_name(ledger_path.stem+'.candidate.json')
    output.write_text(json.dumps(updated,indent=2)+'\n')
    print(json.dumps({'existing_snapshots':len(ledger),'candidate_snapshots':len(updated),
                      'audit':audit,'candidate_path':str(output)},indent=2))
    if any(item['status']=='skipped' for item in audit):
        raise SystemExit('Some fixtures skipped: review audit before publication')

if __name__=='__main__':
    main()
