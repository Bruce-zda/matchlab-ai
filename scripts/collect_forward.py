"""Pre-kickoff forecast collector, driven by a verified UTC kickoff fixture feed.

Usage: python scripts/collect_forward.py fixtures.json ledger.json
Fixture JSON is an array of {league,home,away,kickoff_utc}.
Date-only fixtures are rejected: we never invent kickoff times.
This script does not fetch a live schedule or publish forecasts on its own.
"""
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
from forward_validation import append_snapshot,utc_time,snapshot_id
from bayesian_goals import BayesianGoals
from goal_markets import market_probabilities
from elo_baseline import EloBaseline
from data_quality import valid_score_pair,valid_team_pair
from football_data_provider import get_matches,upcoming_fixtures
import os
import re
import hashlib
import json
from fitted_model_snapshots import pack, unpack, training_digest

LEAGUES={'Premier League':'en.1','La Liga':'es.1','Serie A':'it.1',
         'Bundesliga':'de.1','Ligue 1':'fr.1'}

def models_from_app():
    """Compatibility shim: standalone models, never load the Streamlit app."""
    from football_models import fetch_season,fit_dc,forecast
    return {'fetch_season':fetch_season,'fit_dc':fit_dc,'forecast':forecast}

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
    'newcastleunitedfootballclub':'newcastleunited',
    'astonvilla':'astonvilla',
    'juventus':'juventus',
    'asmonaco':'monaco',
    'monaco':'monaco',
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
    if key.endswith('footballclub'):
        key=key[:-12]
    elif key.endswith('fc'):
        key=key[:-2]
    return TEAM_ALIASES.get(key,key)

def canonicalize_history(history):
    """Merge approved historical spelling variants across both team columns."""
    history=history.copy()
    counts=history['HomeTeam'].value_counts().add(
        history['AwayTeam'].value_counts(),fill_value=0)
    groups={}
    for name in set(history['HomeTeam'].dropna())|set(history['AwayTeam'].dropna()):
        groups.setdefault(team_key(name),[]).append(name)
    replacement={}
    for names in groups.values():
        selected=sorted(names,key=lambda n:(-counts.get(n,0),str(n)))[0]
        replacement.update({n:selected for n in names})
    for column in ('HomeTeam','AwayTeam'):
        history[column]=history[column].replace(replacement)
    return history

def match_team(provider_name,training_names):
    matches=[name for name in training_names if team_key(name)==team_key(provider_name)]
    if len(matches)!=1:
        import difflib
        suggestions=difflib.get_close_matches(team_key(provider_name),
            [team_key(n) for n in training_names],n=3,cutoff=0.5)
        candidates=[n for n in training_names if team_key(n) in suggestions]
        raise ValueError('No unique approved team-name match: '+str(provider_name)+
                         '; training-name candidates (diagnostic only): '+repr(candidates))
    return matches[0]

def collect(fixtures,ledger,now,model_version,preview=False,fitted_cache=None):
    now=utc_time(now)
    ns=models_from_app()
    output=list(ledger)
    audit=[]
    # Optional caller-owned in-memory fitted models. The UTC training cutoff
    # and code revision are part of the key; never reuse across cutoff days.
    cache={} if fitted_cache is None else fitted_cache
    for fixture in fixtures:
        label={k:fixture.get(k) for k in ('league','home','away','kickoff_utc')}
        try:
            league=fixture['league']
            code=LEAGUES[league]
            kickoff=utc_time(fixture['kickoff_utc'])
            if not now<kickoff<=now+dt.timedelta(days=14):
                raise ValueError('Kickoff outside next fourteen days')
            cache_key=(league,now.date().isoformat(),model_version)
            # Remove stale fits on day/version rollover; a worker must never
            # keep accumulating models trained at previous UTC cutoffs.
            for stale_key in list(cache):
                if stale_key[1:] != cache_key[1:]:
                    del cache[stale_key]
            if cache_key not in cache:
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
                history=canonicalize_history(history)
                if len(history)<150:
                    raise ValueError('Insufficient historical training data')
                # Optional persistent snapshot store. Never trust a saved fit
                # without recomputing its training-data digest and cutoff.
                digest=training_digest(history)
                snapshot_dir=os.environ.get('MATCHLAB_FITTED_SNAPSHOT_DIR') if preview else None
                snapshot_file=None
                loaded=None
                if snapshot_dir:
                    folder=pathlib.Path(snapshot_dir)
                    identity=hashlib.sha256(json.dumps([league,cache_key[1],model_version,digest]).encode()).hexdigest()
                    snapshot_file=folder/(identity+'.json')
                    if snapshot_file.is_file():
                        try:
                            loaded=unpack(json.loads(snapshot_file.read_text()),league=league,
                                cutoff_utc_date=cache_key[1],model_version=model_version,
                                history_sha256=digest)
                        except (ValueError,KeyError,TypeError,OverflowError,UnicodeError,json.JSONDecodeError):
                            loaded=None
                if loaded is None:
                    dc=ns['fit_dc'](history)
                    bayes=BayesianGoals().fit(history)
                    elo=EloBaseline()
                    for match in history.itertuples():
                        elo.observe(match.HomeTeam,match.AwayTeam,match.FTHG,match.FTAG)
                    if snapshot_file is not None:
                        try:
                            snapshot_file.parent.mkdir(parents=True,exist_ok=True)
                            content=pack(dc,bayes,elo,league=league,cutoff_utc_date=cache_key[1],
                                model_version=model_version,history_sha256=digest)
                            temp=snapshot_file.with_suffix('.tmp')
                            temp.write_text(json.dumps(content,sort_keys=True,allow_nan=False))
                            temp.replace(snapshot_file)
                        except (OSError,TypeError,ValueError):
                            pass  # Disk cache is optional; never block a valid fresh fit.
                    loaded=(dc,bayes,elo)
                cache[cache_key]=loaded
            dc,bayes,elo=cache[cache_key]
            home=match_team(fixture['home'],dc[0])
            away=match_team(fixture['away'],dc[0])
            if home not in dc[0] or away not in dc[0]:
                raise ValueError('Team names not matched to model training data')
            _,_,grid=ns['forecast'](dc,home,away)
            dc_p=np.array([np.tril(grid,-1).sum(),np.trace(grid),np.triu(grid,1).sum()])
            bayes_grid=bayes.score_grid(home,away)
            bayes_p=np.array([np.tril(bayes_grid,-1).sum(),np.trace(bayes_grid),np.triu(bayes_grid,1).sum()])
            elo_p=elo.predict(home,away)
            probabilities={'Dixon-Coles':dc_p,'Bayesian Goals':bayes_p,
                           'Elo':elo_p,'DC + Bayesian (50/50)':(dc_p+bayes_p)/2}
            side=max(grid.shape[0],grid.shape[1],bayes_grid.shape[0],bayes_grid.shape[1])
            dc_full=np.pad(grid,((0,side-grid.shape[0]),(0,side-grid.shape[1])))
            bayes_full=np.pad(bayes_grid,((0,side-bayes_grid.shape[0]),(0,side-bayes_grid.shape[1])))
            goal_grids={'Dixon-Coles':grid,'Bayesian Goals':bayes_grid,
                        'DC + Bayesian (50/50)':(dc_full+bayes_full)/2}
            new_records=[]
            for model,probs in probabilities.items():
                record={'league':league,'home':home,'away':away,
                        'kickoff_utc':kickoff.isoformat(),
                        'captured_at_utc':now.isoformat(),
                        'model':model,'model_version':model_version,
                        'provider_match_id':fixture.get('provider_match_id'),
                        'p_home':float(probs[0]),'p_draw':float(probs[1]),
                        'p_away':float(probs[2])}
                if model in goal_grids:
                    record['goal_markets']=market_probabilities(goal_grids[model])
                new_records.append(record)
            if preview:
                for record in new_records:
                    record['snapshot_id']=snapshot_id(record)
                    record['preview_only']=True
                output.extend(new_records)
                audit.append({**label,'status':'preview','models':len(new_records)})
                continue
            existing_ids={snapshot_id(item) for item in output}
            fresh=[item for item in new_records if snapshot_id(item) not in existing_ids]
            if fresh and len(fresh)!=len(new_records):
                raise ValueError('Incomplete existing fixture snapshot; manual review required')
            for record in fresh:
                output=append_snapshot(output,record)
            audit.append({**label,'status':'recorded' if fresh else 'already_recorded',
                          'models':len(fresh)})
        except (KeyError,ValueError,TypeError,requests.RequestException) as exc:
            audit.append({**label,'status':'skipped','reason':str(exc)})
    return output,audit

def json_native(value):
    """Convert NumPy scalar values without changing archived forecast semantics."""
    if isinstance(value,np.integer):
        return int(value)
    if isinstance(value,np.floating):
        return float(value)
    if isinstance(value,np.ndarray):
        return value.tolist()
    raise TypeError(f'Unsupported JSON value: {type(value).__name__}')

def main():
    preview='--preview' in sys.argv
    args=[a for a in sys.argv[1:] if a!='--preview']
    if len(args)!=2:
        raise SystemExit('Usage: python scripts/collect_forward.py fixtures.json|--provider ledger.json [--preview]')
    ledger_path=pathlib.Path(args[1])
    if args[0]=='--provider':
        token=os.environ.get('FOOTBALL_DATA_TOKEN','')
        now=dt.datetime.now(dt.timezone.utc)
        matches=get_matches(token,now.date().isoformat(),(now+dt.timedelta(days=7)).date().isoformat())
        fixtures=upcoming_fixtures(matches,now.isoformat())
    else:
        fixtures=json.loads(pathlib.Path(args[0]).read_text())
    ledger=[] if preview else (json.loads(ledger_path.read_text()) if ledger_path.exists() else [])
    if not isinstance(fixtures,list) or not isinstance(ledger,list):
        raise SystemExit('Expected JSON arrays')
    version=__import__('subprocess').check_output(
        ['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    updated,audit=collect(fixtures,ledger,dt.datetime.now(dt.timezone.utc).isoformat(),version,preview=preview)
    # Never overwrite an existing ledger in place. Output a candidate append-only
    # ledger; a separate reviewed publishing process must preserve old snapshots.
    output=(ROOT/'artifacts'/'goal_market_preview.json') if preview else ledger_path.with_name(ledger_path.stem+'.candidate.json')
    output.write_text(json.dumps(updated,indent=2,default=json_native)+'\n')
    coverage={'fixture_count':len(audit),'covered':sum(x['status'] in ('recorded','already_recorded') for x in audit),
              'skipped':sum(x['status']=='skipped' for x in audit),'details':audit,
              'collected_at_utc':dt.datetime.now(dt.timezone.utc).isoformat()}
    if not preview:
        (ROOT/'artifacts'/'forward_coverage.json').write_text(json.dumps(coverage,indent=2,default=json_native)+'\n')
    print(json.dumps({'existing_snapshots':len(ledger),'candidate_snapshots':len(updated),
                      'audit':audit,'candidate_path':str(output)},indent=2,default=json_native))
    recorded=sum(item['status'] in ('recorded','already_recorded','preview') for item in audit)
    skipped=sum(item['status']=='skipped' for item in audit)
    print(f'PREVIEW COVERAGE: {recorded}/{len(audit)} fixtures recorded; {skipped} skipped.')
    for item in audit:
        if item['status']=='skipped':
            print('SKIPPED:',json.dumps(item,ensure_ascii=True,default=json_native))
    if skipped:
        print('WARNING: skipped fixtures require review; this is NOT complete coverage.',file=sys.stderr)
    if recorded==0 and fixtures:
        raise SystemExit('No valid forecasts recorded: collector failed')

if __name__=='__main__':
    main()
