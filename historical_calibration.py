"""Standalone historical calibration research helpers; no Streamlit imports.
Migrated from legacy app.py without altering exploratory evaluation logic.
"""
import datetime as dt
import io
import re
import numpy as np
import pandas as pd
import requests
from scipy.stats import poisson
from football_models import fetch_season,fit_dc,forecast
from calibration import chronological_calibration_report
from data_quality import valid_score_pair,valid_team_pair
LEAGUES={'Premier League':'en.1','La Liga':'es.1','Serie A':'it.1','Bundesliga':'de.1','Ligue 1':'fr.1'}
TODAY=dt.date.today()
OPEN_MATCHDAY='https://raw.githubusercontent.com/oladeeayo/open-matchday/master/data'
FOLDERS={'en.1':'ENG_1_premier-league','es.1':'ESP_1_la-liga','it.1':'ITA_1_serie-a','de.1':'GER_1_bundesliga','fr.1':'FRA_1_ligue-1'}

def matchday_csv(code,kind):
    url=f"{OPEN_MATCHDAY}/{FOLDERS[code]}/{kind}_2627.csv"
    response=requests.get(url,timeout=20)
    response.raise_for_status()
    data=pd.read_csv(io.BytesIO(response.content))
    for col in ('date','home','away'):
        if col not in data:raise ValueError('Missing column '+col)
    if kind=='results' and not {'ft_home','ft_away'}.issubset(data):raise ValueError('Missing result columns')
    result=pd.DataFrame({'Date':pd.to_datetime(data['date'],errors='coerce'),'HomeTeam':data['home'],'AwayTeam':data['away'],'FTHG':pd.to_numeric(data['ft_home'],errors='coerce') if 'ft_home' in data else np.nan,'FTAG':pd.to_numeric(data['ft_away'],errors='coerce') if 'ft_away' in data else np.nan}).dropna(subset=['Date','HomeTeam','AwayTeam'])
    result=result[result.apply(lambda row:valid_team_pair(row.HomeTeam,row.AwayTeam),axis=1)].copy()
    if kind=='results':
        result=result[result.apply(lambda row:valid_score_pair(row.FTHG,row.FTAG),axis=1)]
    return result.drop_duplicates(['Date','HomeTeam','AwayTeam'],keep='last').sort_values('Date').reset_index(drop=True)

def normalized(name):
    name=str(name).lower().replace('&','and')
    name=re.sub(r'[^a-z0-9]','',name)
    aliases={'manutd':'manchesterunited','mancity':'manchestercity','spurs':'tottenhamhotspur','wolves':'wolverhamptonwanderers','newcastle':'newcastleunited','nottmforest':'nottinghamforest','psg':'parissaintgermain','inter':'internazionale','bayern':'bayernmunchen','leeds':'leedsunited','coventry':'coventrycity','hull':'hullcity'}
    return aliases.get(name,name)
def map_team(name,teams):
    import difflib
    keys={normalized(t):t for t in teams}
    key=normalized(name)
    if key in keys:return keys[key]
    close=difflib.get_close_matches(key,list(keys),n=2,cutoff=.9)
    return keys[close[0]] if len(close)==1 else None

def map_team(name,teams):
    import difflib
    keys={normalized(t):t for t in teams}
    key=normalized(name)
    if key in keys:return keys[key]
    close=difflib.get_close_matches(key,list(keys),n=2,cutoff=.9)
    return keys[close[0]] if len(close)==1 else None

def get_league(code):
    """Load up to eight chronological seasons, preserving source gaps."""
    year=TODAY.year if TODAY.month>=7 else TODAY.year-1
    frames=[];errors=[]
    for y in range(year-7,year+1):
        season=f'{y}-{str(y+1)[-2:]}'
        try:
            frame=fetch_season(season,code)
            if frame.empty:
                errors.append(f'{season}: empty archive')
            else:
                frames.append(frame)
        except (requests.RequestException,ValueError,KeyError,TypeError) as exc:
            errors.append(f'{season}: {type(exc).__name__}')
    if not frames:
        return pd.DataFrame(columns=['Date','HomeTeam','AwayTeam','FTHG','FTAG']),errors
    history=pd.concat(frames,ignore_index=True)
    history=history.drop_duplicates(['Date','HomeTeam','AwayTeam'],keep='last')
    return history.sort_values('Date').reset_index(drop=True),errors

def rolling_league_evaluation():
    results=[]
    errors=[]
    for league_name,code in LEAGUES.items():
        try:
            archive,_=get_league(code)
            recent=matchday_csv(code,'results')
            names=set(recent.HomeTeam)|set(recent.AwayTeam)
            for col in ('HomeTeam','AwayTeam'):
                archive[col]=archive[col].map(lambda x:map_team(x,names) or x)
            data=pd.concat([archive,recent],ignore_index=True).sort_values('Date').drop_duplicates(['Date','HomeTeam','AwayTeam'],keep='last')
            data=data[(data.Date.dt.date<TODAY)&data.FTHG.notna()&data.FTAG.notna()].sort_values('Date').reset_index(drop=True)
            if len(data)<350:raise ValueError('Not enough completed matches for rolling evaluation')
            for fold,start_frac in enumerate((.55,.7,.85),start=1):
                begin=int(len(data)*start_frac)
                end=min(len(data),begin+max(40,int(len(data)*.15)))
                # Group boundary by date so all matches played that day stay together.
                cutoff=data.iloc[begin].Date
                end_date=data.iloc[end-1].Date if end<len(data) else data.Date.max()
                train=data[data.Date<cutoff]
                test=data[(data.Date>=cutoff)&(data.Date<=end_date)]
                if len(train)<150 or len(test)<20:continue
                model=fit_dc(train)
                hg=train.FTHG.to_numpy()
                ag=train.FTAG.to_numpy()
                labels=np.where(hg>ag,0,np.where(hg==ag,1,2))
                baseline=np.bincount(labels,minlength=3)/len(labels)
                # Stronger benchmark: smoothed home/away outcome rates for each club.
                # Both club-specific rates use training data only.
                home_counts={}
                away_counts={}
                for row in train.itertuples():
                    outcome=0 if row.FTHG>row.FTAG else 1 if row.FTHG==row.FTAG else 2
                    home_counts.setdefault(row.HomeTeam,np.zeros(3))[outcome]+=1
                    away_counts.setdefault(row.AwayTeam,np.zeros(3))[outcome]+=1
                def club_baseline(home_team,away_team):
                    h=home_counts.get(home_team,np.zeros(3))
                    a=away_counts.get(away_team,np.zeros(3))
                    # Prior strength equivalent to 12 training matches per team.
                    hp=(h+12*baseline)/(h.sum()+12)
                    ap=(a+12*baseline)/(a.sum()+12)
                    return (hp+ap)/2
                preds=[]; actual=[]; strong_preds=[]
                goal_trials=[]
                handicap_trials=[]
                league_home=float(np.mean(hg))
                league_away=float(np.mean(ag))
                # Independent goal-rate benchmark based on training-only venue splits.
                home_for={};home_against={};away_for={};away_against={}
                for row in train.itertuples():
                    home_for.setdefault(row.HomeTeam,[]).append(float(row.FTHG))
                    home_against.setdefault(row.HomeTeam,[]).append(float(row.FTAG))
                    away_for.setdefault(row.AwayTeam,[]).append(float(row.FTAG))
                    away_against.setdefault(row.AwayTeam,[]).append(float(row.FTHG))
                def venue_goal_rates(home,away):
                    def shrink(values,prior):
                        return (sum(values)+8*prior)/(len(values)+8)
                    home_attack=shrink(home_for.get(home,[]),league_home)
                    away_defense=shrink(away_against.get(away,[]),league_home)
                    away_attack=shrink(away_for.get(away,[]),league_away)
                    home_defense=shrink(home_against.get(home,[]),league_away)
                    return max(.15,home_attack*away_defense/max(.1,league_home)),max(.15,away_attack*home_defense/max(.1,league_away))
                def goal_markets(grid):
                    under15=float(grid[0,0]+grid[0,1]+grid[1,0])
                    under25=float(sum(grid[i,j] for i in range(grid.shape[0]) for j in range(grid.shape[1]) if i+j<=2))
                    return np.array([1-under15,1-under25,float(grid[1:,1:].sum())])
                def poisson_grid(lam,mu):
                    counts=np.arange(13)
                    grid=np.outer(poisson.pmf(counts,lam),poisson.pmf(counts,mu))
                    return grid/grid.sum()

                for m in test.itertuples():
                    if m.HomeTeam not in model[0] or m.AwayTeam not in model[0]:continue
                    lam,mu,g=forecast(model,m.HomeTeam,m.AwayTeam)
                    preds.append([float(np.tril(g,-1).sum()),float(np.trace(g)),float(np.triu(g,1).sum())])
                    # Goal-market-only challenger, never used for live predictions.
                    candidate=poisson_grid(.75*lam+.25*league_home,.75*mu+.25*league_away)
                    venue_lam,venue_mu=venue_goal_rates(m.HomeTeam,m.AwayTeam)
                    venue_candidate=poisson_grid(venue_lam,venue_mu)
                    goal_trials.append((goal_markets(g),goal_markets(candidate),goal_markets(venue_candidate),
                                        np.array([m.FTHG+m.FTAG>=2,m.FTHG+m.FTAG>=3,
                                                  m.FTHG>0 and m.FTAG>0],dtype=float)))

                    # Quarter handicap payoff is -1,-0.5,0,+0.5,+1.
                    # Compare forecast expected payoff against realized settlement,
                    # with a training-only empirical goal-difference benchmark.
                    train_diff=(train.FTHG-train.FTAG).to_numpy(dtype=float)
                    match_diff=float(m.FTHG-m.FTAG)
                    for line in (-1.0,-.5,-.25,0.,.25,.5,1.0):
                        def payoff(diff,handicap):
                            q=int(round(handicap*4))
                            def settle(h):
                                return np.sign(diff+h)
                            if abs(q)%2:
                                return .5*(settle(handicap-.25)+settle(handicap+.25))
                            return settle(handicap)
                        pred=float(sum(g[i,j]*payoff(i-j,line) for i in range(g.shape[0]) for j in range(g.shape[1])))
                        prior=float(np.mean([payoff(d,line) for d in train_diff]))
                        observed=float(payoff(match_diff,line))
                        handicap_trials.append((line,pred,prior,observed))
                    strong_preds.append(club_baseline(m.HomeTeam,m.AwayTeam))
                    actual.append(0 if m.FTHG>m.FTAG else 1 if m.FTHG==m.FTAG else 2)
                if len(actual)<20:continue
                p=np.array(preds);y=np.array(actual)
                target=np.eye(3)[y]
                model_brier=float(np.mean((p-target)**2))
                base_brier=float(np.mean((baseline-target)**2))
                strong_brier=float(np.mean((np.array(strong_preds)-target)**2))
                old_goals=np.array([v[0] for v in goal_trials])
                new_goals=np.array([v[1] for v in goal_trials])
                venue_goals=np.array([v[2] for v in goal_trials])
                goal_truth=np.array([v[3] for v in goal_trials])
                goal_base=np.array([np.mean(hg+ag>=2),np.mean(hg+ag>=3),np.mean((hg>0)&(ag>0))])
                old_goal_brier=float(np.mean((old_goals-goal_truth)**2))
                new_goal_brier=float(np.mean((new_goals-goal_truth)**2))
                baseline_goal_brier=float(np.mean((goal_base-goal_truth)**2))
                venue_goal_brier=float(np.mean((venue_goals-goal_truth)**2))
                per_market={}
                for idx,market in enumerate(('Over 1.5','Over 2.5','BTTS')):
                    per_market[market+' current']=float(np.mean((old_goals[:,idx]-goal_truth[:,idx])**2))
                    per_market[market+' challenger']=float(np.mean((new_goals[:,idx]-goal_truth[:,idx])**2))
                    per_market[market+' baseline']=float(np.mean((goal_base[idx]-goal_truth[:,idx])**2))
                    per_market[market+' venue']=float(np.mean((venue_goals[:,idx]-goal_truth[:,idx])**2))
                for line in (-1.0,-.5,-.25,0.,.25,.5,1.0):
                    h=np.array([v[1:] for v in handicap_trials if v[0]==line],dtype=float)
                    if len(h):
                        per_market[f'AH {line:+.2f} model MSE']=float(np.mean((h[:,0]-h[:,2])**2))
                        per_market[f'AH {line:+.2f} baseline MSE']=float(np.mean((h[:,1]-h[:,2])**2))
                for market,idxs in (('1X',(0,1)),('X2',(1,2)),('12',(0,2))):
                    pp=p[:,list(idxs)].sum(axis=1)
                    bp=np.array(strong_preds)[:,list(idxs)].sum(axis=1)
                    yy=np.isin(y,idxs).astype(float)
                    per_market[f'{market} model Brier']=float(np.mean((pp-yy)**2))
                    per_market[f'{market} club Brier']=float(np.mean((bp-yy)**2))
                # Exploratory chronological calibration: predictions in this fold
                # are all out-of-sample relative to the DC fit. Calibrator sees
                # only the earlier part of the fold; later outcomes remain hidden.
                # No calibrated probabilities enter live predictions.
                calibration_metrics={}
                if len(y)>=60:
                    for market,idxs in (('1X',(0,1)),('X2',(1,2)),('12',(0,2))):
                        binary_p=p[:,list(idxs)].sum(axis=1)
                        binary_y=np.isin(y,idxs).astype(float)
                        report=chronological_calibration_report(binary_p,binary_y)
                        calibration_metrics[f'{market} calibration raw Brier']=report['raw_brier']
                        calibration_metrics[f'{market} calibration adjusted Brier']=report['calibrated_brier']
                        calibration_metrics[f'{market} calibration evaluation n']=report['evaluation_n']
                results.append({'League':league_name,'Fold':fold,'Test start':str(cutoff.date()),'Test matches':len(y),'Accuracy':float(np.mean(p.argmax(axis=1)==y)),'Model Brier':model_brier,'Baseline Brier':base_brier,'Club baseline Brier':strong_brier,'Improvement':base_brier-model_brier,'Club improvement':strong_brier-model_brier,'Current goals Brier':old_goal_brier,'Challenger goals Brier':new_goal_brier,'Goal baseline Brier':baseline_goal_brier,'Venue model Brier':venue_goal_brier,'Challenger gain':old_goal_brier-new_goal_brier,**per_market,**calibration_metrics})
        except Exception as exc:
            errors.append(f'{league_name}: {type(exc).__name__}: {str(exc)[:90]}')
    return pd.DataFrame(results),errors
