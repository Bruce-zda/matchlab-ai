import datetime as dt
import io
import html
import re
import numpy as np
import pandas as pd
import requests
import streamlit as st
from scipy.optimize import minimize
from scipy.stats import poisson
from calibration import chronological_calibration_report
from selection_policy import MarketEvidence, assess_market_evidence, describe_candidate, rank_model_outlooks
from data_quality import valid_score_pair, valid_team_pair
from odds_intelligence import SPORT_KEYS, compare_h2h
from model_performance import show_model_performance
from forward_performance import show_forward_performance
from discover import show_discover

st.set_page_config(page_title='MatchLab | Football Intelligence', page_icon='⚽', layout='wide')
st.markdown("""<style>
.block-container{max-width:980px;padding:2.8rem 1.25rem 4rem}
[data-testid="stAppViewContainer"]{background:#0d1117;color:#e6e9ed}
[data-testid="stHeader"]{background:#0d1117}
h1,h2,h3{letter-spacing:-.03em}
.stTabs [data-baseweb="tab-list"]{gap:8px;border-bottom:1px solid #303741}
.stTabs [data-baseweb="tab"]{font-size:.9rem;padding:10px 14px}
.stTabs [aria-selected="true"]{color:#e5e9ed!important}
div[data-testid="stMetric"]{background:#161d26;border:1px solid #29333e;border-radius:9px;padding:12px}
div[data-testid="stMetricValue"]{color:#f0f2f5}
div[data-testid="stAlert"]{border-radius:8px}
.brand{display:flex;align-items:baseline;gap:10px;border-bottom:1px solid #29333e;padding:0 0 19px;margin-bottom:20px}
.brand b{font-size:1.5rem;letter-spacing:-.05em}
.brand span{font-size:.7rem;letter-spacing:.13em;color:#a6afb9}
.match-card{border:1px solid #303945;background:#151b24;border-radius:11px;padding:22px;margin:18px 0}
.match-card .label{font-size:.72rem;color:#9faab6;letter-spacing:.14em;font-weight:700}
.match-card .fixture{font-size:clamp(1.35rem,4vw,2.15rem);font-weight:750;margin:14px 0}
.match-card .pick{color:#c2ccd4;font-size:.93rem}
.status{border-left:3px solid #d5ad65;background:#1a2028;padding:12px 15px;margin:14px 0;font-size:.87rem;color:#cbd3dc}
.analysis-title{font-size:1.05rem;font-weight:750;margin:24px 0 9px}
.form-strip{font-family:monospace;letter-spacing:.15em;font-size:1.05rem}
@media(max-width:640px){.block-container{padding:2rem .9rem 3rem}.match-card{padding:16px}.brand b{font-size:1.3rem}}

/* MatchLab mobile-first release styling */
:root{color-scheme:dark}
html,body,[data-testid="stAppViewContainer"]{font-family:Inter,ui-sans-serif,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
[data-testid="stAppViewContainer"]{background:radial-gradient(ellipse at 75% -15%,#192331 0%,#0c1017 38%,#0c1017 100%)}
.block-container{max-width:1050px;padding-top:2.2rem}
.brand{margin-bottom:12px;padding-bottom:16px;border-bottom:1px solid #29313b}
.brand b{font-size:1.65rem;font-weight:850;letter-spacing:-.07em}
.brand span{font-size:.63rem;font-weight:650;color:#94a2b3}
.match-card{background:linear-gradient(135deg,#1c2934,#121923 70%);border:1px solid #344352;border-radius:16px;padding:30px;box-shadow:0 16px 36px #05070b40}
.match-card .label{color:#e1b86e}
.match-card .fixture{line-height:1.22;font-size:clamp(1.55rem,4.5vw,2.6rem)}
.match-card .pick{font-size:1rem;color:#cdd7df}
.status{border-left:2px solid #d5ad65;background:#171f29;border-radius:0 9px 9px 0}
.analysis-title{font-size:1.22rem;font-weight:780;letter-spacing:-.035em;margin:30px 0 14px}
[data-testid="stMetric"]{min-width:0}
div[data-testid="stMetric"]{border-radius:12px;background:#171f29;border-color:#2c3948;padding:17px}
div[data-testid="stMetricValue"]{font-weight:730;letter-spacing:-.04em}
div[data-testid="stVerticalBlock"]>div{min-width:0}
.stTabs [data-baseweb="tab-list"]{overflow-x:auto;scrollbar-width:none;flex-wrap:nowrap}
.stTabs [data-baseweb="tab"]{white-space:nowrap}
.stButton button[kind="primary"]{background:#d6ae68;color:#121923;border:none;border-radius:9px;font-weight:750}
.stButton button[kind="primary"]:hover{background:#e9c98c;color:#121923}
.stButton button[kind="secondary"],.stDownloadButton button{border:1px solid #34404e;border-radius:9px;background:#18212c;color:#e2e9ef}
[data-testid="stDataFrame"]{border:1px solid #293544;border-radius:10px;overflow:hidden}
@media(max-width:650px){
.block-container{padding:1.25rem .85rem 3rem}
.brand{align-items:center;flex-wrap:wrap;gap:5px 12px}
.brand b{font-size:1.5rem}
.brand span{font-size:.58rem}
.match-card{padding:20px 17px}
.match-card .fixture{font-size:1.7rem}
div[data-testid="stMetric"]{padding:11px}
div[data-testid="stMetricValue"]{font-size:1.35rem}
.stTabs [data-baseweb="tab"]{font-size:.83rem;padding:9px 11px}
}

/* Editorial match-centre layout: deliberate typography and thumb-friendly controls */
[data-testid="stAppViewContainer"]{background:#0b1017;color:#eef2f6}
.block-container{max-width:1040px}
.brand{border-bottom:1px solid #27313d;padding-bottom:22px}
.brand b{font-size:1.9rem;letter-spacing:-.065em}
.match-card{background:linear-gradient(125deg,#1b2c3c 0%,#131e2a 62%,#151b24 100%);border:1px solid #3a4b5c;border-radius:18px;padding:34px 32px}
.match-card .fixture{font-size:clamp(1.65rem,4.5vw,2.65rem);margin:20px 0 14px}
.match-card .pick{color:#d5dee8}
.analysis-title{font-size:1.28rem;margin:34px 0 16px}
.insight-card{background:#151e29;border:1px solid #344657;border-radius:15px;padding:24px;margin:18px 0}
.insight-eyebrow{font-size:.73rem;letter-spacing:.12em;text-transform:uppercase;color:#dcb977;font-weight:750}
.insight-pick{font-size:clamp(1.5rem,4vw,2.25rem);font-weight:800;letter-spacing:-.04em;margin:10px 0}
.insight-note{color:#aebdca;font-size:.88rem;line-height:1.6}
.prob-row{display:flex;align-items:center;justify-content:space-between;gap:16px;font-size:.93rem;margin:14px 0 7px}
.prob-track{height:8px;background:#2a3440;border-radius:99px;overflow:hidden}
.prob-fill{height:100%;border-radius:99px;background:linear-gradient(90deg,#9bafbe,#e2bb78)}
[data-testid="stDataFrame"]{border-radius:12px}
@media(max-width:650px){
.block-container{padding:1.1rem 1rem 4rem!important}
.brand b{font-size:1.7rem}
.match-card{padding:24px 19px;border-radius:15px}
.match-card .fixture{font-size:1.85rem;line-height:1.25}
.insight-card{padding:20px 17px}
.analysis-title{font-size:1.17rem;margin-top:27px}
[data-testid="stMarkdownContainer"] p{line-height:1.65}
.stTabs [data-baseweb="tab"]{font-size:.91rem;min-height:46px}
[data-testid="stSelectbox"]>div,[data-testid="stRadio"]{min-height:44px}
}

/* MatchLab compact editorial match view */
.match-card{padding:25px 27px;margin:12px 0 14px;border-radius:14px;box-shadow:none}
.match-card .label,.insight-eyebrow{font-size:.66rem;letter-spacing:.16em}
.match-card .fixture{margin:12px 0 15px;line-height:1.15}
.fixture-divider{font-size:.55em;color:#8594a3;font-weight:550;vertical-align:middle;margin:0 .18em}
.match-card .pick{display:flex;align-items:center;gap:10px;flex-wrap:wrap;font-size:.85rem;color:#9baebf}
.match-card .pick strong{color:#f3f5f7}
.result-prob{margin-left:auto;background:#273a46;border:1px solid #3a4c57;border-radius:7px;padding:5px 9px;color:#f1c783;font-weight:800;font-variant-numeric:tabular-nums}
.insight-card{padding:19px 23px;margin:12px 0 13px;background:#141d27}
.insight-pick{font-size:clamp(1.18rem,3vw,1.55rem);line-height:1.2;margin:10px 0 7px}
.insight-note{font-size:.87rem;line-height:1.45}
.insight-foot{border-top:1px solid #2a3643;margin-top:13px;padding-top:10px;color:#8191a1;font-size:.73rem}
.analysis-title{margin:20px 0 10px;font-size:1.08rem}
.prob-row{margin:11px 0 6px}
@media(max-width:650px){
.block-container{padding:.85rem .9rem 3rem!important}
.match-card{padding:18px 17px;margin:9px 0 12px}
.match-card .fixture{font-size:clamp(1.42rem,6vw,1.85rem);margin:11px 0 13px}
.match-card .pick{gap:6px;font-size:.81rem}
.result-prob{margin-left:0}
.insight-card{padding:17px;margin:10px 0}
.insight-pick{font-size:1.28rem}
.analysis-title{margin:16px 0 9px}
[data-testid="stMarkdownContainer"] p{line-height:1.5}
}
</style>""",unsafe_allow_html=True)
st.markdown('<div class="brand"><b>MATCHLAB<span style="color:#d5ad65">.</span></b><span>FOOTBALL INTELLIGENCE</span></div>',unsafe_allow_html=True)
show_discover()
st.divider()
@st.cache_data(ttl=3600)
def load_csv(upload):
    df=pd.read_csv(upload)
    needed={'Date','HomeTeam','AwayTeam','FTHG','FTAG'}
    if not needed.issubset(df.columns):
        raise ValueError('CSV must contain: '+', '.join(sorted(needed)))
    df=df.copy()
    df['Date']=pd.to_datetime(df['Date'],dayfirst=True,errors='coerce')
    for c in ['FTHG','FTAG']:
        df[c]=pd.to_numeric(df[c],errors='coerce')
    df=df.dropna(subset=['Date','HomeTeam','AwayTeam','FTHG','FTAG']).sort_values('Date')
    df=df[(df.FTHG>=0)&(df.FTAG>=0)]
    return df

def fit_dc(df, half_life=365):
    teams=sorted(set(df.HomeTeam)|set(df.AwayTeam)); n=len(teams)
    ids={t:i for i,t in enumerate(teams)}
    hi=df.HomeTeam.map(ids).to_numpy(); ai=df.AwayTeam.map(ids).to_numpy()
    hg=df.FTHG.to_numpy().astype(int); ag=df.FTAG.to_numpy().astype(int)
    days=(df.Date.max()-df.Date).dt.days.to_numpy()
    weights=np.exp(-np.log(2)*days/half_life)
    def unpack(p):
        attack=np.r_[p[:n-1],-np.sum(p[:n-1])]
        defense=np.r_[p[n-1:2*n-2],-np.sum(p[n-1:2*n-2])]
        return attack,defense,p[-3],p[-2],p[-1]
    def loss(p):
        attack,defense,home,base,rho=unpack(p)
        lam=np.exp(np.clip(base+home+attack[hi]+defense[ai],-5,4))
        mu=np.exp(np.clip(base+attack[ai]+defense[hi],-5,4))
        ll=poisson.logpmf(hg,lam)+poisson.logpmf(ag,mu)
        tau=np.ones(len(hg))
        m=(hg==0)&(ag==0);tau[m]=1-lam[m]*mu[m]*rho
        m=(hg==0)&(ag==1);tau[m]=1+lam[m]*rho
        m=(hg==1)&(ag==0);tau[m]=1+mu[m]*rho
        m=(hg==1)&(ag==1);tau[m]=1-rho
        if (tau<=0).any():return 1e12
        return -np.sum(weights*(ll+np.log(tau)))+0.015*np.sum(p[:-3]**2)
    init=np.r_[np.zeros(2*(n-1)),0.2,np.log(max((hg.mean()+ag.mean())/2,0.2)),0.0]
    bounds=[(-2.5,2.5)]*(2*(n-1))+[(0,1.5),(-2,1.5),(-0.15,0.15)]
    res=minimize(loss,init,method='L-BFGS-B',bounds=bounds,options={'maxiter':400})
    if not res.success: st.warning('Optimizer did not fully converge; treat results cautiously.')
    attack,defense,home,base,rho=unpack(res.x)
    return teams,dict(zip(teams,attack)),dict(zip(teams,defense)),home,base,rho

def forecast(model,home_team,away_team,max_goals=12):
    teams,attack,defense,home,base,rho=model
    lam=float(np.exp(base+home+attack[home_team]+defense[away_team]))
    mu=float(np.exp(base+attack[away_team]+defense[home_team]))
    goals=np.arange(max_goals+1)
    grid=np.outer(poisson.pmf(goals,lam),poisson.pmf(goals,mu))
    grid[0,0]*=1-lam*mu*rho
    grid[0,1]*=1+lam*rho
    grid[1,0]*=1+mu*rho
    grid[1,1]*=1-rho
    grid=np.maximum(grid,0);grid/=grid.sum()
    return lam,mu,grid


LEAGUES={'Premier League':'en.1','La Liga':'es.1','Serie A':'it.1','Bundesliga':'de.1','Ligue 1':'fr.1'}
TODAY=dt.date.today()

OPEN_MATCHDAY='https://raw.githubusercontent.com/oladeeayo/open-matchday/master/data'
FOLDERS={'en.1':'ENG_1_premier-league','es.1':'ESP_1_la-liga','it.1':'ITA_1_serie-a','de.1':'GER_1_bundesliga','fr.1':'FRA_1_ligue-1'}
@st.cache_data(ttl=3600,show_spinner=False)
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
@st.cache_data(ttl=900,show_spinner=False)
def fetch_market_odds(sport_key,api_key):
    response=requests.get(
        f'https://api.the-odds-api.com/v4/sports/{sport_key}/odds/',
        params={'apiKey':api_key,'regions':'eu','markets':'h2h','oddsFormat':'decimal'},
        timeout=15,
    )
    response.raise_for_status()
    payload=response.json()
    if not isinstance(payload,list):
        raise ValueError('Unexpected odds response')
    return payload

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

@st.cache_data(ttl=21600,show_spinner=False)
def fetch_season(season,code):
    url=f'https://raw.githubusercontent.com/openfootball/football.json/master/{season}/{code}.json'
    response=requests.get(url,timeout=20)
    response.raise_for_status()
    payload=response.json()
    games=payload.get('matches') or [m for r in payload.get('rounds',[]) for m in r.get('matches',[])]
    rows=[]
    for match in games:
        date=pd.to_datetime(match.get('date'),errors='coerce')
        if pd.isna(date):continue
        score=match.get('score')
        ft=score.get('ft') if isinstance(score,dict) else score if isinstance(score,list) else None
        if isinstance(ft,dict):ft=[ft.get('home'),ft.get('away')]
        if not isinstance(ft,list) or len(ft)<2:ft=[None,None]
        def name(v):return v.get('name',v.get('key','Unknown')) if isinstance(v,dict) else str(v)
        rows.append(dict(Date=date,HomeTeam=name(match.get('team1','')),AwayTeam=name(match.get('team2','')),FTHG=pd.to_numeric(ft[0],errors='coerce'),FTAG=pd.to_numeric(ft[1],errors='coerce')))
    frame=pd.DataFrame(rows,columns=['Date','HomeTeam','AwayTeam','FTHG','FTAG'])
    if frame.empty:return frame
    frame=frame[frame.apply(lambda row:valid_team_pair(row.HomeTeam,row.AwayTeam),axis=1)]
    frame=frame[frame.apply(lambda row:valid_score_pair(row.FTHG,row.FTAG),axis=1)]
    return frame.drop_duplicates(['Date','HomeTeam','AwayTeam'],keep='last').reset_index(drop=True)
@st.cache_data(ttl=21600,show_spinner=False)
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

@st.cache_data(ttl=21600,show_spinner=False)
def train_cached(df):
    return fit_dc(df)

@st.cache_data(ttl=3600,show_spinner=False)
def cross_league_evaluation():
    output=[]
    failures=[]
    for league_name,code in LEAGUES.items():
        try:
            archive,_=get_league(code)
            results=matchday_csv(code,'results')
            fixtures=matchday_csv(code,'fixtures')
            names=set(results.HomeTeam)|set(results.AwayTeam)|set(fixtures.HomeTeam)|set(fixtures.AwayTeam)
            for col in ('HomeTeam','AwayTeam'):
                archive[col]=archive[col].map(lambda x:map_team(x,names) or x)
            data=pd.concat([archive,results],ignore_index=True).sort_values('Date').drop_duplicates(['Date','HomeTeam','AwayTeam'],keep='last')
            data=data[(data.Date.dt.date<TODAY)&data.FTHG.notna()&data.FTAG.notna()].sort_values('Date').reset_index(drop=True)
            if len(data)<150:raise ValueError('Fewer than 150 matches')
            cutoff=data.iloc[int(len(data)*.8)].Date
            training=data[data.Date<cutoff]
            testing=data[data.Date>=cutoff]
            if len(training)<100:raise ValueError('Insufficient training rows')
            model=fit_dc(training)
            yh=training.FTHG.to_numpy()
            ya=training.FTAG.to_numpy()
            outcomes=np.where(yh>ya,0,np.where(yh==ya,1,2))
            baseline=np.bincount(outcomes,minlength=3)/len(outcomes)
            train_total=yh+ya
            market_baseline={
                'Home win':baseline[0],'Draw':baseline[1],'Away win':baseline[2],
                '1X':baseline[0]+baseline[1],'X2':baseline[1]+baseline[2],'12':baseline[0]+baseline[2],
                'Over 1.5':float(np.mean(train_total>=2)),
                'Over 2.5':float(np.mean(train_total>=3)),
                'Under 2.5':float(np.mean(train_total<=2)),
                'Under 3.5':float(np.mean(train_total<=3)),
                'BTTS Yes':float(np.mean((yh>0)&(ya>0))),
                'BTTS No':float(np.mean((yh==0)|(ya==0)))
            }
            samples=[]
            for m in testing.itertuples():
                if m.HomeTeam not in model[0] or m.AwayTeam not in model[0]:continue
                _,_,g=forecast(model,m.HomeTeam,m.AwayTeam)
                p=np.array([np.tril(g,-1).sum(),np.trace(g),np.triu(g,1).sum()])
                result=0 if m.FTHG>m.FTAG else 1 if m.FTHG==m.FTAG else 2
                total=int(m.FTHG+m.FTAG)
                under25=float(sum(g[i,j] for i in range(g.shape[0]) for j in range(g.shape[1]) if i+j<=2))
                under35=float(sum(g[i,j] for i in range(g.shape[0]) for j in range(g.shape[1]) if i+j<=3))
                btts=float(g[1:,1:].sum())
                values={'Home win':p[0],'Draw':p[1],'Away win':p[2],'1X':p[0]+p[1],'X2':p[1]+p[2],'12':p[0]+p[2],'Over 1.5':1-float(g[0,0]+g[0,1]+g[1,0]),'Over 2.5':1-under25,'Under 2.5':under25,'Under 3.5':under35,'BTTS Yes':btts,'BTTS No':1-btts}
                actual={'Home win':result==0,'Draw':result==1,'Away win':result==2,'1X':result!=2,'X2':result!=0,'12':result!=1,'Over 1.5':total>=2,'Over 2.5':total>=3,'Under 2.5':total<=2,'Under 3.5':total<=3,'BTTS Yes':m.FTHG>0 and m.FTAG>0,'BTTS No':m.FTHG==0 or m.FTAG==0}
                samples.append((result,p,values,actual))
            if len(samples)<25:raise ValueError('Too few test fixtures')
            actual_out=np.array([x[0] for x in samples])
            probabilities=np.array([x[1] for x in samples])
            model_brier=float(np.mean((probabilities-np.eye(3)[actual_out])**2))
            base_brier=float(np.mean((baseline-np.eye(3)[actual_out])**2))
            output.append({'League':league_name,'Market':'1X2 overall','Matches':len(samples),'Model Brier':model_brier,'Baseline Brier':base_brier,'Improvement':base_brier-model_brier,'Accuracy':float(np.mean(probabilities.argmax(axis=1)==actual_out)),'Cutoff':str(cutoff.date())})
            for name,base in market_baseline.items():
                ps=np.array([x[2][name] for x in samples],dtype=float)
                ys=np.array([x[3][name] for x in samples],dtype=float)
                mb=float(np.mean((ps-ys)**2))
                bb=float(np.mean((base-ys)**2))
                output.append({'League':league_name,'Market':name,'Matches':len(samples),'Model Brier':mb,'Baseline Brier':bb,'Improvement':bb-mb,'Accuracy':float(np.mean((ps>=.5)==ys)),'Cutoff':str(cutoff.date())})
        except Exception as exc:
            failures.append(f'{league_name}: {type(exc).__name__}: {str(exc)[:90]}')
    return pd.DataFrame(output),failures


@st.cache_data(ttl=3600,show_spinner=False)
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

def team_stats(data,team,venue=None,n=5):
    games=data[(data.HomeTeam==team)|(data.AwayTeam==team)].sort_values('Date',ascending=False)
    if venue=='home':games=games[games.HomeTeam==team]
    if venue=='away':games=games[games.AwayTeam==team]
    games=games.head(n)
    if games.empty:return None
    scored=np.where(games.HomeTeam==team,games.FTHG,games.FTAG)
    conceded=np.where(games.HomeTeam==team,games.FTAG,games.FTHG)
    wins=int(np.sum(scored>conceded))
    draws=int(np.sum(scored==conceded))
    losses=int(np.sum(scored<conceded))
    form=''.join('W' if x>y else 'D' if x==y else 'L' for x,y in zip(scored[::-1],conceded[::-1]))
    return dict(n=len(games),wins=wins,draws=draws,losses=losses,gf=float(np.mean(scored)),ga=float(np.mean(conceded)),form=form)
def show_card(model,home,away,data):
    lam,mu,grid=forecast(model,home,away)
    probs=[float(np.tril(grid,-1).sum()),float(np.trace(grid)),float(np.triu(grid,1).sum())]
    winner=['Home win','Draw','Away win'][int(np.argmax(probs))]
    safe_home,safe_away=html.escape(home),html.escape(away)
    st.markdown(
        f'<div class="match-card"><div class="label">MATCH PREVIEW</div>'
        f'<div class="fixture">{safe_home} <span class="fixture-divider">vs</span> {safe_away}</div>'
        f'<div class="pick">Most likely result <strong>{winner}</strong>'
        f'<span class="result-prob">{max(probs):.1%}</span></div></div>',
        unsafe_allow_html=True)
    under25=float(sum(grid[i,j] for i in range(grid.shape[0]) for j in range(grid.shape[1]) if i+j<=2))
    under35=float(sum(grid[i,j] for i in range(grid.shape[0]) for j in range(grid.shape[1]) if i+j<=3))
    btts=float(grid[1:,1:].sum())
    markets={
        'Home win':probs[0], 'Draw':probs[1], 'Away win':probs[2],
        'Home or draw (1X)':probs[0]+probs[1],
        'Draw or away (X2)':probs[1]+probs[2],
        'Home or away (12)':probs[0]+probs[2],
        'Over 1.5 goals':1-float(grid[0,0]+grid[0,1]+grid[1,0]),
        'Over 2.5 goals':1-under25,'Under 2.5 goals':under25,
        'Under 3.5 goals':under35,
        'Both teams to score — Yes':btts,
        'Both teams to score — No':1-btts
    }
    # These development-fold benchmarks are exploratory and must never imply an edge.
    # Only historically supported double-chance markets enter descriptive ranking.
    evidence_status = {
        'Home or draw (1X)': assess_market_evidence(MarketEvidence('1X',15,13,.193,.204)),
        'Draw or away (X2)': assess_market_evidence(MarketEvidence('X2',15,13,.219,.228)),
        'Home or away (12)': assess_market_evidence(MarketEvidence('12',15,10,.186,.188)),
    }
    dc_probabilities = {
        'Home or draw (1X)': probs[0]+probs[1],
        'Draw or away (X2)': probs[1]+probs[2],
        'Home or away (12)': probs[0]+probs[2],
    }
    outlook = rank_model_outlooks(dc_probabilities,evidence_status)
    if outlook['status'] == 'ABSTAIN':
        confidence_label='No clear market advantage'
        confidence_detail='The strongest supported markets are closely matched.'
    else:
        ranked_name,ranked_probability=outlook['ranking'][0]
        confidence_label='Preliminary market outlook'
        confidence_detail=f'{ranked_name} · {ranked_probability:.1%} estimated probability'
    st.markdown(
        f'<div class="insight-card"><div class="insight-eyebrow">MODEL ASSESSMENT</div>'
        f'<div class="insight-pick">{html.escape(confidence_label)}</div>'
        f'<div class="insight-note">{html.escape(confidence_detail)}</div>'
        f'<div class="insight-foot">Research-stage assessment · not a verified betting edge</div></div>',
        unsafe_allow_html=True)
    with st.expander('How this assessment is evaluated'):
        st.caption('Double-chance screening uses exploratory historical folds. 1X and X2 beat the club baseline in 13/15 folds; 12 in 10/15. These folds informed development, so independent validation remains necessary. No bookmaker odds are available to assess betting value.')
    ranked_markets=sorted(markets.items(),key=lambda item:item[1],reverse=True)
    st.markdown('**Compare double-chance probabilities**')
    for market_name,probability in [('Home or draw · 1X',probs[0]+probs[1]),('Draw or away · X2',probs[1]+probs[2]),('Home or away · 12',probs[0]+probs[2])]:
        st.markdown(f'<div class="prob-row"><span>{html.escape(market_name)}</span><strong>{probability:.1%}</strong></div><div class="prob-track"><div class="prob-fill" style="width:{max(0,min(100,probability*100)):.1f}%"></div></div>',unsafe_allow_html=True)
    st.caption('Probabilities describe outcomes, not betting value.')
    with st.expander('Explore all supported markets'):
        st.dataframe(pd.DataFrame([{'Market':name,'Model probability':f'{p:.1%}'} for name,p in ranked_markets]),hide_index=True,use_container_width=True)

    st.markdown('<div class="analysis-title">Outcome probabilities</div>',unsafe_allow_html=True)
    a,b,c=st.columns(3)
    a.metric('Home',f'{probs[0]:.1%}')
    b.metric('Draw',f'{probs[1]:.1%}')
    c.metric('Away',f'{probs[2]:.1%}')
    st.markdown('<div class="analysis-title">Match analysis</div>',unsafe_allow_html=True)
    home_form=team_stats(data,home)
    away_form=team_stats(data,away)
    home_venue=team_stats(data,home,'home')
    away_venue=team_stats(data,away,'away')
    if home_form and away_form:
        left,right=st.columns(2)
        with left:
            st.markdown(f'**{home}** · Last {home_form["n"]}')
            st.markdown(f'<div class="form-strip">{home_form["form"]}</div>',unsafe_allow_html=True)
            st.caption(f'{home_form["wins"]}W · {home_form["draws"]}D · {home_form["losses"]}L')
        with right:
            st.markdown(f'**{away}** · Last {away_form["n"]}')
            st.markdown(f'<div class="form-strip">{away_form["form"]}</div>',unsafe_allow_html=True)
            st.caption(f'{away_form["wins"]}W · {away_form["draws"]}D · {away_form["losses"]}L')
        comparison=pd.DataFrame({
            'Measure':['Recent goals scored / match','Recent goals conceded / match','Venue goals scored / match','Venue goals conceded / match'],
            home:[home_form['gf'],home_form['ga'],home_venue['gf'] if home_venue else np.nan,home_venue['ga'] if home_venue else np.nan],
            away:[away_form['gf'],away_form['ga'],away_venue['gf'] if away_venue else np.nan,away_venue['ga'] if away_venue else np.nan]
        })
        st.dataframe(comparison,hide_index=True,use_container_width=True)
    h2h=data[((data.HomeTeam==home)&(data.AwayTeam==away))|((data.HomeTeam==away)&(data.AwayTeam==home))].sort_values('Date',ascending=False).head(5)
    with st.expander(f'Head-to-head · {len(h2h)} recorded meetings'):
        if h2h.empty:st.write('No recorded meetings in this dataset.')
        else:
            for m in h2h.itertuples():
                st.write(f'{m.Date.date()} · {m.HomeTeam} {int(m.FTHG)}–{int(m.FTAG)} {m.AwayTeam}')
            st.caption('Head-to-head is descriptive, not a causal predictor.')
    st.markdown('<div class="analysis-title">How the model sees this match</div>',unsafe_allow_html=True)
    reasons=[f'The model estimates {lam:.2f} goals for {home} and {mu:.2f} for {away}, using team attacking and defensive strength plus a home advantage term.']
    if home_form and away_form:
        reasons.append(f'Across their last five recorded matches, {home} averaged {home_form["gf"]:.2f} goals scored and {away} averaged {away_form["gf"]:.2f}. These are context, not separate model inputs.')
    if home_venue and away_venue:
        reasons.append(f'At the relevant venues, {home} scored {home_venue["gf"]:.2f} per home match and {away} scored {away_venue["gf"]:.2f} per away match (up to five games each).')
    for reason in reasons:st.write(reason)
    st.caption('No verified lineups, injuries, live form feed or tactical assessment. Avoid interpreting this as a complete scouting report.')
    with st.expander('Asian handicap calculator · advanced'):
        side=st.radio('Asian handicap side',['Home','Away'],horizontal=True,key=f'ah_side_{home}_{away}')
        handicap=st.select_slider('Handicap applied to selected team',options=[x/4 for x in range(-8,9)],value=0.0,key=f'ah_line_{home}_{away}')
        selected_team=home if side=='Home' else away
        st.markdown(f'**Selected handicap: {selected_team} {handicap:+.2f}**')
        st.caption('A positive handicap gives the selected team a head start; a negative handicap requires a stronger result.')
        def settle_line(diff,line):
            adjusted=diff+line
            if adjusted>1e-9:return 1.
            if adjusted< -1e-9:return -1.
            return 0.
        def asian_settlement(diff,line):
            # Quarter lines split the stake evenly between adjacent half-lines.
            q=int(round(line*4))
            if abs(q)%2==1:
                return (settle_line(diff,line-.25)+settle_line(diff,line+.25))/2
            return settle_line(diff,line)
        settlement={'Full win':0.,'Half win':0.,'Push':0.,'Half loss':0.,'Full loss':0.}
        for i in range(grid.shape[0]):
            for j in range(grid.shape[1]):
                diff=(i-j) if side=='Home' else (j-i)
                value=asian_settlement(diff,handicap)
                label={1.:'Full win',.5:'Half win',0.:'Push',-.5:'Half loss',-1.:'Full loss'}[value]
                settlement[label]+=float(grid[i,j])
        st.dataframe(pd.DataFrame([{'Settlement':key,'Estimated probability':f'{value:.1%}'} for key,value in settlement.items()]),hide_index=True,use_container_width=True)
        st.caption(f'Estimated full-or-half-win probability: {settlement["Full win"]+settlement["Half win"]:.1%}; push probability: {settlement["Push"]:.1%}. Half-wins are not equivalent to full wins.')
        st.caption('Quarter-goal lines split the stake between adjacent half-lines. A push returns the stake; half outcomes settle half the stake. These are unvalidated model estimates, not a recommended bet. Corners require a separate verified corner-statistics dataset.')
    st.caption('Asian handicap estimates are exploratory, not betting recommendations. Corners need verified event data.')
    top=sorted(((i,j,float(grid[i,j])) for i in range(grid.shape[0]) for j in range(grid.shape[1])),key=lambda x:x[2],reverse=True)[:3]
    st.write('**Likely scorelines:** '+' · '.join(f'{i}–{j} ({p:.1%})' for i,j,p in top))
    with st.expander('Full statistical breakdown'):
        a,b=st.columns(2)
        a.metric('Home model goals',f'{lam:.2f}')
        b.metric('Away model goals',f'{mu:.2f}')
        under=float(sum(grid[i,j] for i in range(grid.shape[0]) for j in range(grid.shape[1]) if i+j<=2))
        a.metric('Over 2.5',f'{1-under:.1%}')
        b.metric('Both teams score',f'{grid[1:,1:].sum():.1%}')
        st.dataframe(pd.DataFrame(grid[:6,:6]).style.format('{:.1%}'),use_container_width=True)
        st.caption('Model expected goals are not event-data xG. Probabilities have not been calibrated.')

st.caption('Data-driven match analysis · Probabilities, not guarantees.')
league=st.selectbox('Choose league',list(LEAGUES))
with st.spinner('Loading football results and fixtures…'):
    raw,errors=get_league(LEAGUES[league])
    upcoming=pd.DataFrame()
    data_source='OpenFootball (fallback)'
    new_results=pd.DataFrame()
    try:
        new_results=matchday_csv(LEAGUES[league],'results')
        data_source='open-matchday results + OpenFootball archive'
    except (requests.RequestException,ValueError,KeyError,pd.errors.ParserError) as exc:
        st.warning(f'Results feed unavailable ({type(exc).__name__}); historical fallback in use.')
    try:
        upcoming=matchday_csv(LEAGUES[league],'fixtures')
    except (requests.RequestException,ValueError,KeyError,pd.errors.ParserError) as exc:
        st.info(f'Upcoming fixture feed unavailable ({type(exc).__name__}); schedule may be incomplete.')
    if not new_results.empty:
        current_names=set(new_results.HomeTeam)|set(new_results.AwayTeam)
        if not upcoming.empty:
            current_names|=set(upcoming.HomeTeam)|set(upcoming.AwayTeam)
        archive=raw.copy()
        for col in ('HomeTeam','AwayTeam'):
            archive[col]=archive[col].map(lambda x:map_team(x,current_names) or x)
        archive=archive.dropna(subset=['HomeTeam','AwayTeam'])
        raw=pd.concat([archive,new_results],ignore_index=True).sort_values('Date').drop_duplicates(['Date','HomeTeam','AwayTeam'],keep='last')

if raw.empty:
    st.error('No football records available for this league.')
    st.stop()
played=raw[(raw.Date.dt.date<TODAY)&raw.FTHG.notna()&raw.FTAG.notna()].copy()
future=upcoming[upcoming.Date.dt.date>=TODAY].copy() if not upcoming.empty else raw[(raw.Date.dt.date>=TODAY)&(raw.FTHG.isna()|raw.FTAG.isna())].copy()
last=played.Date.max().date() if not played.empty else None
age=(TODAY-last).days if last else None
freshness='CURRENT' if age is not None and age<=7 else 'DELAYED' if age is not None and age<=14 else 'STALE'
if len(played)<100:
    st.error('Insufficient completed matches to train the model.')
    st.stop()
with st.spinner('Fitting Dixon–Coles model…'):
    model=train_cached(played)
teams=model[0]
tab1,tab2,tab3,tab4=st.tabs(['Upcoming fixtures','Manual matchup','Historical test','All leagues'])
with tab1:
    st.caption('Community-maintained fixture list · Confirm kick-off times independently.')
    if future.empty:st.info('No upcoming fixtures listed. Try manual matchup.')
    else:
        options=future.head(100).reset_index(drop=True)
        k=st.selectbox('Select fixture',range(len(options)),format_func=lambda i:f'{options.iloc[i].Date.date()} · {options.iloc[i].HomeTeam} vs {options.iloc[i].AwayTeam}')
        m=options.iloc[k]
        h=map_team(m.HomeTeam,teams)
        a=map_team(m.AwayTeam,teams)
        if h and a and h!=a:
            show_card(model,h,a,played)
            with st.expander('Market intelligence · bookmaker comparison',expanded=False):
                st.caption('Independent market prices only. Bookmaker odds never enter MatchLab’s forecasting model or expert selection.')
                odds_key=st.secrets.get('ODDS_API_KEY','')
                if not odds_key:
                    st.info('Optional odds feed not connected. Add ODDS_API_KEY to Streamlit app secrets to enable bookmaker comparisons.')
                elif st.button('Load current market prices',key='load_market_odds'):
                    try:
                        odds_events=fetch_market_odds(SPORT_KEYS[league],odds_key)
                        odds_rows=compare_h2h(odds_events,h,a,m.Date.date(),normalized)
                        if odds_rows:
                            st.dataframe(pd.DataFrame(odds_rows),hide_index=True,use_container_width=True)
                            st.caption('No-vig probabilities remove the displayed bookmaker margin; they are not model probabilities. Prices can change.')
                        else:
                            st.info('No unambiguous three-way bookmaker prices found for this fixture.')
                    except (requests.RequestException,ValueError,KeyError) as exc:
                        st.warning(f'Odds currently unavailable ({type(exc).__name__}). Model prediction is unaffected.')
        else:st.info('One team has no recorded results yet.')
with tab2:
    home=st.selectbox('Home team',teams)
    away=st.selectbox('Away team',[t for t in teams if t!=home])
    show_card(model,home,away,played)
with tab3:
    st.caption('Chronological 80/20 holdout. One fixed model trained before the test period; no future scores enter training. This is an initial test, not full rolling validation.')
    if st.button('Run market-by-market evaluation',type='primary'):
        ordered=played.sort_values('Date').reset_index(drop=True)
        cutoff=ordered.iloc[int(len(ordered)*0.8)].Date
        train=ordered[ordered.Date<cutoff].copy()
        test=ordered[ordered.Date>=cutoff].copy()
        if len(train)<100:
            st.error('Insufficient training data.')
        else:
            with st.spinner('Evaluating unseen matches…'):
                held_model=fit_dc(train)
                train_h=train.FTHG.to_numpy()
                train_a=train.FTAG.to_numpy()
                train_outcome=np.where(train_h>train_a,0,np.where(train_h==train_a,1,2))
                baseline_1x2=np.bincount(train_outcome,minlength=3)/len(train_outcome)
                train_total=train_h+train_a
                baseline_market=np.array([
                    baseline_1x2[0],baseline_1x2[1],baseline_1x2[2],
                    baseline_1x2[0]+baseline_1x2[1],
                    baseline_1x2[1]+baseline_1x2[2],
                    baseline_1x2[0]+baseline_1x2[2],
                    np.mean(train_total>=2),np.mean(train_total>=3),
                    np.mean(train_total<=2),np.mean(train_total<=3),
                    np.mean((train_h>0)&(train_a>0)),
                    np.mean((train_h==0)|(train_a==0))
                ])
                records=[]
                markets=['Home win','Draw','Away win','1X','X2','12','Over 1.5','Over 2.5','Under 2.5','Under 3.5','BTTS Yes','BTTS No']
                for m in test.itertuples():
                    if m.HomeTeam not in held_model[0] or m.AwayTeam not in held_model[0]:continue
                    _,_,g=forecast(held_model,m.HomeTeam,m.AwayTeam)
                    p=np.array([np.tril(g,-1).sum(),np.trace(g),np.triu(g,1).sum()])
                    outcome=0 if m.FTHG>m.FTAG else 1 if m.FTHG==m.FTAG else 2
                    total=int(m.FTHG+m.FTAG)
                    scored_both=bool(m.FTHG>0 and m.FTAG>0)
                    u25=sum(g[i,j] for i in range(g.shape[0]) for j in range(g.shape[1]) if i+j<=2)
                    u35=sum(g[i,j] for i in range(g.shape[0]) for j in range(g.shape[1]) if i+j<=3)
                    bt=float(g[1:,1:].sum())
                    q=[p[0],p[1],p[2],p[0]+p[1],p[1]+p[2],p[0]+p[2],1-float(g[0,0]+g[0,1]+g[1,0]),1-u25,u25,u35,bt,1-bt]
                    y=[outcome==0,outcome==1,outcome==2,outcome!=2,outcome!=0,outcome!=1,total>=2,total>=3,total<=2,total<=3,scored_both,not scored_both]
                    records.append(dict(Date=m.Date.date(),Match=f'{m.HomeTeam} vs {m.AwayTeam}',actual=outcome,guess=int(p.argmax()),brier=float(np.mean((p-np.eye(3)[outcome])**2)),logloss=float(-np.log(max(p[outcome],1e-12))),exact=int(tuple(np.unravel_index(np.argmax(g),g.shape))==(int(m.FTHG),int(m.FTAG))),probs=q,actuals=y))
            if not records:
                st.error('No eligible holdout fixtures.')
            else:
                a,b,c,d=st.columns(4)
                a.metric('Test matches',len(records))
                b.metric('1X2 accuracy',f'{np.mean([r["actual"]==r["guess"] for r in records]):.1%}')
                c.metric('1X2 Brier ↓',f'{np.mean([r["brier"] for r in records]):.3f}')
                d.metric('Log loss ↓',f'{np.mean([r["logloss"] for r in records]):.3f}')
                baseline_brier=float(np.mean([np.mean((baseline_1x2-np.eye(3)[r['actual']])**2) for r in records]))
                model_brier=float(np.mean([r['brier'] for r in records]))
                st.write(f'**Simple baseline (training-set home/draw/away frequencies):** Brier {baseline_brier:.3f} · MatchLab {model_brier:.3f}')
                if model_brier>=baseline_brier:
                    st.error('Validation gate NOT PASSED: MatchLab does not beat the simple 1X2 baseline on this holdout.')
                else:
                    st.success('MatchLab beats the simple 1X2 baseline on this holdout. Broader testing is still required.')
                st.caption(f'Train: {len(train)} matches before {cutoff.date()} · Test: {len(records)} matches from {cutoff.date()} · Exact-score hit: {np.mean([r["exact"] for r in records]):.1%}')
                if len(records)<100:st.warning('Small holdout sample: treat market hit rates as exploratory, not reliable.')
                rows=[]
                for k,name in enumerate(markets):
                    ps=np.array([r['probs'][k] for r in records],dtype=float)
                    ys=np.array([r['actuals'][k] for r in records],dtype=float)
                    chosen=ps>=.75
                    rows.append({'Market':name,'Brier ↓':round(float(np.mean((ps-ys)**2)),3),'Baseline Brier ↓':round(float(np.mean((baseline_market[k]-ys)**2)),3),'Beats baseline':bool(np.mean((ps-ys)**2)<np.mean((baseline_market[k]-ys)**2)),'Mean predicted':round(float(ps.mean()),3),'Observed rate':round(float(ys.mean()),3),'P≥75% picks':int(chosen.sum()),'Hit rate at ≥75%':f'{ys[chosen].mean():.1%}' if chosen.any() else '—'})
                st.subheader('Market reliability')
                st.dataframe(pd.DataFrame(rows),hide_index=True,use_container_width=True)
                st.caption('Brier: lower is better. The ≥75% threshold was not optimized on this test. High hit rate alone does not establish betting value; odds and independent validation are missing.')
                export=pd.DataFrame([{k:v for k,v in r.items() if k not in ('probs','actuals')} for r in records])
                st.download_button('Export holdout results',export.to_csv(index=False),file_name='matchlab_holdout.csv',mime='text/csv')
with tab4:
    st.subheader('Cross-league validation')
    st.caption('One click evaluates all five leagues on separate chronological 80/20 holdouts. Each league is trained and tested independently.')
    if st.button('Evaluate all five leagues',type='primary'):
        with st.spinner('Loading and testing all competitions. This can take a few minutes…'):
            evaluation,failures=cross_league_evaluation()
        if failures:
            for failure in failures:st.warning(failure)
        if evaluation.empty:
            st.error('No leagues could be evaluated. Check the data feeds.')
        else:
            overall=evaluation[evaluation.Market=='1X2 overall'].copy()
            st.markdown('**Match result performance by league**')
            st.dataframe(overall[['League','Matches','Accuracy','Model Brier','Baseline Brier','Improvement','Cutoff']].style.format({'Accuracy':'{:.1%}','Model Brier':'{:.3f}','Baseline Brier':'{:.3f}','Improvement':'{:+.3f}'}),hide_index=True,use_container_width=True)
            st.caption('Positive improvement means the model beats the simple historical-frequency baseline.')
            detail=evaluation[evaluation.Market!='1X2 overall']
            summary=detail.groupby('Market').agg(Leagues=('League','nunique'),Beats=('Improvement',lambda v:int((v>0).sum())),Mean_improvement=('Improvement','mean'),Total_matches=('Matches','sum')).reset_index()
            st.markdown('**Market consistency across leagues**')
            st.dataframe(summary,hide_index=True,use_container_width=True)
            st.caption('Do not use this dashboard to tune thresholds on the same holdouts. Cross-league results are exploratory; rolling-origin testing and an untouched final test set are still required.')
            st.download_button('Download cross-league results',evaluation.to_csv(index=False),file_name='matchlab_cross_league.csv',mime='text/csv')
    st.divider()
    st.subheader('Rolling-origin validation')
    st.caption('Three chronological folds per league. Every fold retrains using only earlier results. This is a stronger stress test than one 80/20 split, but still not a fully untouched final evaluation.')
    if st.button('Run rolling validation across five leagues'):
        with st.spinner('Training up to 15 historical models. This may take several minutes…'):
            rolling,rolling_errors=rolling_league_evaluation()
        for issue in rolling_errors:st.warning(issue)
        if rolling.empty:
            st.error('No rolling folds completed.')
        else:
            st.dataframe(rolling.style.format({'Accuracy':'{:.1%}','Model Brier':'{:.3f}','Baseline Brier':'{:.3f}','Club baseline Brier':'{:.3f}','Improvement':'{:+.3f}','Club improvement':'{:+.3f}'}),hide_index=True,use_container_width=True)
            grouped=rolling.groupby('League').agg(Folds=('Fold','count'),Matches=('Test matches','sum'),Positive_folds=('Improvement',lambda x:int((x>0).sum())),Club_baseline_wins=('Club improvement',lambda x:int((x>0).sum())),Mean_improvement=('Improvement','mean'),Mean_club_improvement=('Club improvement','mean')).reset_index()
            st.markdown('**Consistency by competition**')
            st.dataframe(grouped.style.format({'Mean_improvement':'{:+.3f}','Mean_club_improvement':'{:+.3f}'}),hide_index=True,use_container_width=True)
            st.caption('Two training-only benchmarks: league-wide frequencies and a stronger smoothed team home/away outcome model. Positive club improvement means MatchLab beats that stronger benchmark. Folds can be correlated and do not guarantee future performance.')
            st.markdown('**Double chance — rolling validation**')
            dc_validation=[]
            for market in ('1X','X2','12'):
                model_col=rolling[f'{market} model Brier']
                base_col=rolling[f'{market} club Brier']
                dc_validation.append({'Market':market,'Model Brier':float(model_col.mean()),'Club baseline Brier':float(base_col.mean()),'Beats club baseline':int((model_col<base_col).sum()),'Folds':len(rolling)})
            st.dataframe(pd.DataFrame(dc_validation).style.format({'Model Brier':'{:.3f}','Club baseline Brier':'{:.3f}'}),hide_index=True,use_container_width=True)
            st.caption('Double chance is evaluated as a binary event against the training-only club-specific baseline. No odds or betting value assessed.')
            st.markdown('**Expert-pick evidence screening**')
            policy_rows=[]
            for row in dc_validation:
                status=assess_market_evidence(MarketEvidence(
                    row['Market'],row['Folds'],row['Beats club baseline'],
                    row['Model Brier'],row['Club baseline Brier']))
                policy_rows.append({'Market':row['Market'],'Evidence status':status,
                                    'Expert pick':'Not endorsed — no verified odds or untouched final test'})
            st.dataframe(pd.DataFrame(policy_rows),hide_index=True,use_container_width=True)
            st.caption('Preliminary support means historical model reliability only, never a bet recommendation. The system abstains from expert picks until independent final testing and verified odds are available.')

            st.markdown('**Asian handicap — settlement validation**')
            ah_validation=[]
            for line in (-1.0,-.5,-.25,0.,.25,.5,1.0):
                model_col=rolling[f'AH {line:+.2f} model MSE']
                base_col=rolling[f'AH {line:+.2f} baseline MSE']
                ah_validation.append({'Home handicap':f'{line:+.2f}','Model settlement MSE':float(model_col.mean()),'Baseline settlement MSE':float(base_col.mean()),'Beats baseline':int((model_col<base_col).sum()),'Folds':len(rolling)})
            st.dataframe(pd.DataFrame(ah_validation).style.format({'Model settlement MSE':'{:.3f}','Baseline settlement MSE':'{:.3f}'}),hide_index=True,use_container_width=True)
            st.caption('Settlement score uses −1 full loss, −0.5 half loss, 0 push, +0.5 half win, +1 full win. Lower mean squared error is better. Benchmark is the historical training-only goal-difference distribution. These tests do not establish profitability.')
            st.markdown('**Goal-model challenger (experimental)**')
            st.caption('Compares current goal-market forecasts with a 25% training-league-rate shrinkage model. Both are scored on the same held-out fixtures across Over 1.5, Over 2.5 and BTTS. This challenger does NOT change live predictions.')
            goals_view=rolling[['League','Fold','Test matches','Current goals Brier','Challenger goals Brier','Goal baseline Brier','Challenger gain']].copy()
            st.dataframe(goals_view.style.format({'Current goals Brier':'{:.3f}','Challenger goals Brier':'{:.3f}','Goal baseline Brier':'{:.3f}','Challenger gain':'{:+.3f}'}),hide_index=True,use_container_width=True)
            gain_wins=int((rolling['Challenger gain']>0).sum())
            baseline_wins=int((rolling['Challenger goals Brier']<rolling['Goal baseline Brier']).sum())
            st.info(f'Challenger improves on the existing model in {gain_wins}/{len(rolling)} folds and beats the goals baseline in {baseline_wins}/{len(rolling)} folds. This is not yet sufficient to replace the live model.')
            market_rows=[]
            for market in ('Over 1.5','Over 2.5','BTTS'):
                current=rolling[market+' current']
                challenger=rolling[market+' challenger']
                baseline_goals=rolling[market+' baseline']
                market_rows.append({'Market':market,'Challenger beats current':int((challenger<current).sum()),'Challenger beats baseline':int((challenger<baseline_goals).sum()),'Total folds':len(rolling),'Average current Brier':float(current.mean()),'Average challenger Brier':float(challenger.mean()),'Average baseline Brier':float(baseline_goals.mean())})
            st.markdown('**Independent venue-based goals benchmark**')
            st.caption('A separate model uses training-only home/away scoring and conceding rates with eight-match smoothing. Lower Brier is better. It is not deployed to live forecasts.')
            venue_table=rolling[['League','Fold','Test matches','Current goals Brier','Venue model Brier','Goal baseline Brier']].copy()
            st.dataframe(venue_table.style.format({'Current goals Brier':'{:.3f}','Venue model Brier':'{:.3f}','Goal baseline Brier':'{:.3f}'}),hide_index=True,use_container_width=True)
            st.info(f"Venue model beats current goals forecast in {int((rolling['Venue model Brier']<rolling['Current goals Brier']).sum())}/{len(rolling)} folds and simple baseline in {int((rolling['Venue model Brier']<rolling['Goal baseline Brier']).sum())}/{len(rolling)} folds.")
            st.markdown('**Goal-market breakdown**')
            st.dataframe(pd.DataFrame(market_rows).style.format({'Average current Brier':'{:.3f}','Average challenger Brier':'{:.3f}','Average baseline Brier':'{:.3f}'}),hide_index=True,use_container_width=True)
            st.markdown('**Goal-model promotion gate**')
            if baseline_wins < len(rolling)*.6:
                st.warning(f'NOT PASSED — the challenger beat the simple goals baseline in only {baseline_wins}/{len(rolling)} folds. Live goal predictions remain unchanged.')
            else:
                st.info('Preliminary consistency threshold met, but no promotion without an untouched final test and per-market checks.')
            st.caption('The 60% fold threshold is a screening rule, not a statistical significance test. These folds have already been examined during development.')
            st.caption('Exploratory diagnostic only. These historical folds have already influenced development; a separate untouched final test is necessary before promoting any challenger.')

            st.markdown('**Experimental Double Chance calibration**')
            st.caption('Within each historical fold, the model is frozen before the fold. A calibrator is fitted on the earlier 65% of its out-of-sample forecasts, then assessed on the later 35%. This is exploratory: folds overlap across training histories and are not an untouched final test.')
            calibration_rows=[]
            for market in ('1X','X2','12'):
                raw_key=f'{market} calibration raw Brier'
                adj_key=f'{market} calibration adjusted Brier'
                if raw_key in rolling.columns:
                    valid=rolling[[raw_key,adj_key]].dropna()
                    if not valid.empty:
                        calibration_rows.append({'Market':market,'Folds':len(valid),'Improved folds':int((valid[adj_key]<valid[raw_key]).sum()),'Raw Brier':float(valid[raw_key].mean()),'Calibrated Brier':float(valid[adj_key].mean())})
            if calibration_rows:
                st.dataframe(pd.DataFrame(calibration_rows).style.format({'Raw Brier':'{:.4f}','Calibrated Brier':'{:.4f}'}),hide_index=True,use_container_width=True)
                st.warning('Experimental only — no calibrated probabilities are deployed. An untouched evaluation is still required.')
            else:
                st.info('Insufficient historical fold samples for the calibration experiment.')
            st.download_button('Download rolling validation',rolling.to_csv(index=False),file_name='matchlab_rolling.csv',mime='text/csv')

st.divider()
show_forward_performance()
st.divider()
show_model_performance()

with st.expander('About the data and limitations'):
    st.caption('Daily data: open-matchday (non-commercial use only; upstream rights apply). Historical: OpenFootball. No live scores or paid API.')
    st.markdown('Attribution: [open-matchday](https://github.com/oladeeayo/open-matchday) · [OpenFootball](https://github.com/openfootball/football.json)')

st.divider()
with st.expander(f'Data health · {freshness}', expanded=False):
    st.markdown(f'<div class="status"><b>DATA HEALTH: {freshness}</b> · Latest recorded result: {last} · {age if age is not None else "?"} days old<br>{len(played):,} completed matches · {len(future):,} unverified upcoming fixtures</div>',unsafe_allow_html=True)
    if age is not None and age>14:
        st.warning('⚠️ Results are stale. Forecasts may miss recent form; fixture dates are not independently verified.')
    elif age is not None and age>7:
        st.info('Results are delayed. Confirm match schedules independently.')
    if errors:st.caption('Unavailable historical seasons: '+', '.join(errors))
