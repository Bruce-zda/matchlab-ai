"""Reproducible, same-fixture chronological Dixon-Coles vs Elo comparison.

Exploratory historical evaluation, NOT an untouched final test.
Run: python scripts/model_comparison.py
"""
import ast
import datetime as dt
import json
import pathlib
import sys
import numpy as np
import pandas as pd
import requests
from scipy.optimize import minimize
from scipy.stats import poisson

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from data_quality import valid_score_pair, valid_team_pair
from elo_baseline import EloBaseline

source = (ROOT / 'app.py').read_text()
tree = ast.parse(source)
names = {'fit_dc', 'forecast', 'fetch_season'}
nodes = []
for node in tree.body:
    if isinstance(node, ast.FunctionDef) and node.name in names:
        node.decorator_list = []
        nodes.append(node)
if {n.name for n in nodes} != names:
    raise RuntimeError('Model function contract changed')
# Streamlit warning is only invoked for optimizer nonconvergence.
class WarningSink:
    @staticmethod
    def warning(message):
        print('MODEL WARNING:', message)

namespace = {'np': np, 'pd': pd, 'requests': requests,
             'minimize': minimize, 'poisson': poisson,
             'valid_score_pair': valid_score_pair, 'valid_team_pair': valid_team_pair,
             'st': WarningSink}
exec(compile(ast.fix_missing_locations(ast.Module(body=nodes, type_ignores=[])),
             str(ROOT / 'app.py'), 'exec'), namespace)

LEAGUES = {'Premier League': 'en.1', 'La Liga': 'es.1', 'Serie A': 'it.1',
           'Bundesliga': 'de.1', 'Ligue 1': 'fr.1'}

def score(probabilities, actual):
    p = np.asarray(probabilities, dtype=float)
    if p.shape != (3,) or not np.isfinite(p).all() or (p < 0).any() or abs(p.sum()-1) > 1e-6:
        raise ValueError('Invalid probabilities')
    return float(np.mean((p - np.eye(3)[actual]) ** 2)), float(-np.log(max(p[actual], 1e-12)))

def run():
    year = dt.date.today().year if dt.date.today().month >= 7 else dt.date.today().year - 1
    rows = []
    failures = []
    for league, code in LEAGUES.items():
        frames = []
        for y in range(year-7, year+1):
            season = f'{y}-{str(y+1)[-2:]}'
            try:
                frame = namespace['fetch_season'](season, code)
                if not frame.empty:
                    frames.append(frame)
            except (requests.RequestException, ValueError, KeyError, TypeError) as exc:
                failures.append(f'{league} {season}: {type(exc).__name__}')
        if not frames:
            failures.append(f'{league}: no usable seasons')
            continue
        data = pd.concat(frames).drop_duplicates(['Date','HomeTeam','AwayTeam'])
        data = data[data.Date.dt.date < dt.date.today()].sort_values(['Date','HomeTeam','AwayTeam']).reset_index(drop=True)
        if len(data) < 400:
            failures.append(f'{league}: only {len(data)} matches')
            continue
        # Three nonoverlapping test windows; each uses only earlier fixtures.
        for fold, fraction in enumerate((0.55, 0.70, 0.85), 1):
            start = data.iloc[int(len(data)*fraction)].Date
            end_index = min(len(data)-1, int(len(data)*(fraction+0.15))-1)
            end = data.iloc[end_index].Date
            train = data[data.Date < start]
            test = data[(data.Date >= start) & (data.Date <= end)]
            if len(train) < 150 or len(test) < 20:
                continue
            dc = namespace['fit_dc'](train)
            elo = EloBaseline()
            for match in train.itertuples():
                elo.observe(match.HomeTeam, match.AwayTeam, match.FTHG, match.FTAG)
            # Frozen models within each test fold: neither model sees test outcomes.
            for match in test.itertuples():
                if match.HomeTeam not in dc[0] or match.AwayTeam not in dc[0]:
                    continue
                _, _, grid = namespace['forecast'](dc, match.HomeTeam, match.AwayTeam)
                dc_p = (float(np.tril(grid,-1).sum()),float(np.trace(grid)),float(np.triu(grid,1).sum()))
                elo_p = elo.predict(match.HomeTeam, match.AwayTeam)
                actual = 0 if match.FTHG > match.FTAG else 1 if match.FTHG == match.FTAG else 2
                for model, probabilities in (('Dixon-Coles', dc_p), ('Elo', elo_p)):
                    brier, logloss = score(probabilities, actual)
                    rows.append({'league':league,'fold':fold,'date':match.Date.date().isoformat(),
                                 'home':match.HomeTeam,'away':match.AwayTeam,'model':model,
                                 'p_home':probabilities[0],'p_draw':probabilities[1],
                                 'p_away':probabilities[2],'actual':actual,
                                 'brier':brier,'log_loss':logloss})
        print(f'{league}: {len(data)} completed matches, {len(rows)} cumulative model predictions', flush=True)
    out = ROOT / 'artifacts'
    out.mkdir(exist_ok=True)
    frame = pd.DataFrame(rows)
    if frame.empty:
        raise SystemExit('No paired model predictions')
    frame.to_csv(out/'model_comparison_predictions.csv', index=False)
    grouped = frame.groupby('model').agg(predictions=('brier','size'),
                                        mean_brier=('brier','mean'),
                                        mean_log_loss=('log_loss','mean'))
    summary = {'evaluation':'exploratory_frozen_chronological_folds_not_untouched',
               'models':grouped.reset_index().to_dict(orient='records'),
               'leagues':frame.league.nunique(),
               'paired_fixtures':len(frame)//2,
               'data_errors':failures,
               'caveats':['Previously explored seasons; not an untouched holdout',
                          'Models frozen within each test fold',
                          'Teams unseen in Dixon-Coles training excluded from both',
                          'No bookmaker inputs']}
    (out/'model_comparison.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary,indent=2))
    if frame.league.nunique()!=5 or len(frame)<400:
        raise SystemExit('Insufficient paired coverage')

if __name__=='__main__':
    run()
