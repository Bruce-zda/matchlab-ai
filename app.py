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

st.set_page_config(page_title='MatchLab AI V2', page_icon='⚽', layout='wide')
st.markdown("""<style>
:root{color-scheme:dark}
.block-container{max-width:1040px;padding-top:1.2rem;padding-bottom:3rem}
[data-testid="stAppViewContainer"]{background:radial-gradient(ellipse at 85% 0%,#183e36 0%,#0d161b 34%,#0b1117 70%);color:#edf8f3}
[data-testid="stHeader"]{background:transparent}
h1,h2,h3{letter-spacing:-.035em}
h1{font-size:clamp(2rem,5vw,3.3rem)!important}
div[data-testid="stMetric"]{background:#17242b;border:1px solid #30413f;border-radius:16px;padding:14px}
div[data-testid="stMetricValue"]{color:#7ff5b0}
.stTabs [data-baseweb="tab-list"]{gap:10px;overflow-x:auto}
.stTabs [data-baseweb="tab"]{background:#17242b;border-radius:12px 12px 0 0;padding:10px 14px}
.stTabs [aria-selected="true"]{color:#7ff5b0!important}
div[data-testid="stAlert"]{border-radius:14px}
.hero{border:1px solid #325348;background:linear-gradient(125deg,#193a32,#142129);border-radius:22px;padding:22px 24px;margin:8px 0 20px}
.hero .eyebrow{color:#85f5b2;font-size:.8rem;font-weight:800;letter-spacing:.13em}
.hero h1{margin:.2rem 0 .35rem}
.hero p{margin:0;color:#bbd0ca}
.match-card{background:#16252b;border:1px solid #315047;border-radius:22px;padding:20px;margin:16px 0}
.match-card .label{color:#8aeeb3;font-size:.78rem;letter-spacing:.11em;font-weight:800}
.match-card .fixture{font-size:clamp(1.25rem,3.5vw,2rem);font-weight:800;margin:10px 0}
.match-card .pick{color:#d8eee5}
.status{border:1px solid #4e694d;background:#283526;border-radius:14px;padding:14px 17px;margin:10px 0;color:#f1eec7}
@media(max-width:640px){.block-container{padding-left:1rem;padding-right:1rem}.hero,.match-card{padding:17px}.stTabs [data-baseweb="tab"]{padding:8px}}
</style>""",unsafe_allow_html=True)
st.markdown("""<div class="hero"><div class="eyebrow">MATCH INTELLIGENCE · PROTOTYPE</div>
<h1>⚽ MatchLab AI <span style="color:#86f5b2">V2.1</span></h1>
<p>Five major leagues · fixture forecasts · transparent probabilities</p></div>""",unsafe_allow_html=True)

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
    return pd.DataFrame({'Date':pd.to_datetime(data['date'],errors='coerce'),'HomeTeam':data['home'],'AwayTeam':data['away'],'FTHG':pd.to_numeric(data['ft_home'],errors='coerce') if 'ft_home' in data else np.nan,'FTAG':pd.to_numeric(data['ft_away'],errors='coerce') if 'ft_away' in data else np.nan}).dropna(subset=['Date','HomeTeam','AwayTeam'])
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
    return pd.DataFrame(rows,columns=['Date','HomeTeam','AwayTeam','FTHG','FTAG'])
@st.cache_data(ttl=21600,show_spinner=False)
def get_league(code):
    year=TODAY.year if TODAY.month>=7 else TODAY.year-1
    frames=[];errors=[]
    for y in (year-2,year-1,year):
        season=f'{y}-{str(y+1)[-2:]}'
        try:frames.append(fetch_season(season,code))
        except Exception as e:errors.append(f'{season}: {type(e).__name__}')
    if not frames:return pd.DataFrame(),errors
    return pd.concat(frames,ignore_index=True).drop_duplicates(['Date','HomeTeam','AwayTeam']).sort_values('Date'),errors
@st.cache_data(ttl=21600,show_spinner=False)
def train_cached(df):
    return fit_dc(df)
def show_card(model,home,away):
    lam,mu,grid=forecast(model,home,away)
    probs=[float(np.tril(grid,-1).sum()),float(np.trace(grid)),float(np.triu(grid,1).sum())]
    winner=['Home win','Draw','Away win'][int(np.argmax(probs))]
    safe_home,safe_away=html.escape(home),html.escape(away)
    st.markdown(f'<div class="match-card"><div class="label">MATCH FORECAST</div><div class="fixture">{safe_home} <span style="color:#86f5b2">vs</span> {safe_away}</div><div class="pick">Model pick: <b>{winner}</b> · {max(probs):.1%} estimated probability</div></div>',unsafe_allow_html=True)
    a,b,c=st.columns(3)
    a.metric('Home win',f'{probs[0]:.1%}')
    b.metric('Draw',f'{probs[1]:.1%}')
    c.metric('Away win',f'{probs[2]:.1%}')
    st.progress(float(max(probs)),text=f'Model confidence in top outcome: {max(probs):.1%} (not calibrated confidence)')
    top=sorted(((i,j,float(grid[i,j])) for i in range(grid.shape[0]) for j in range(grid.shape[1])),key=lambda x:x[2],reverse=True)[:3]
    st.write('**Top exact scores:** '+' · '.join(f'{i}–{j} ({p:.1%})' for i,j,p in top))
    with st.expander('Advanced analysis'):
        a,b=st.columns(2)
        a.metric('Home expected goals',f'{lam:.2f}')
        b.metric('Away expected goals',f'{mu:.2f}')
        under=float(sum(grid[i,j] for i in range(grid.shape[0]) for j in range(grid.shape[1]) if i+j<=2))
        a.metric('Over 2.5 goals',f'{1-under:.1%}')
        b.metric('Both teams score',f'{grid[1:,1:].sum():.1%}')
        st.write('**Exact score probabilities** (home goals = rows)')
        st.dataframe(pd.DataFrame(grid[:6,:6]).style.format('{:.1%}'),use_container_width=True)
        st.caption('Time-decayed Dixon–Coles. No injuries, lineup changes, or live odds included.')

st.caption('Research prototype · Not betting advice · Estimates are not guarantees.')
league=st.selectbox('Choose league',list(LEAGUES))
with st.spinner('Loading football results and fixtures…'):
    raw,errors=get_league(LEAGUES[league])
    upcoming=pd.DataFrame()
    data_source='OpenFootball (fallback)'
    try:
        new_results=matchday_csv(LEAGUES[league],'results')
        upcoming=matchday_csv(LEAGUES[league],'fixtures')
        current_names=set(new_results.HomeTeam)|set(new_results.AwayTeam)|set(upcoming.HomeTeam)|set(upcoming.AwayTeam)
        archive=raw.copy()
        for col in ('HomeTeam','AwayTeam'):
            archive[col]=archive[col].map(lambda x:map_team(x,current_names))
        archive=archive.dropna(subset=['HomeTeam','AwayTeam'])
        raw=pd.concat([archive,new_results],ignore_index=True).sort_values('Date').drop_duplicates(['Date','HomeTeam','AwayTeam'],keep='last')
        data_source='open-matchday daily feed + OpenFootball archive'
    except Exception as exc:
        st.warning(f'Open-matchday feed unavailable ({type(exc).__name__}); historical fallback in use.')

if raw.empty:
    st.error('No football records available for this league.')
    st.stop()
played=raw[(raw.Date.dt.date<TODAY)&raw.FTHG.notna()&raw.FTAG.notna()].copy()
future=upcoming[upcoming.Date.dt.date>=TODAY].copy() if not upcoming.empty else raw[(raw.Date.dt.date>=TODAY)&(raw.FTHG.isna()|raw.FTAG.isna())].copy()
last=played.Date.max().date() if not played.empty else None
age=(TODAY-last).days if last else None
freshness='CURRENT' if age is not None and age<=7 else 'DELAYED' if age is not None and age<=14 else 'STALE'
st.markdown(f'<div class="status"><b>DATA HEALTH: {freshness}</b> · Latest recorded result: {last} · {age if age is not None else "?"} days old<br>{len(played):,} completed matches · {len(future):,} unverified upcoming fixtures · Source: {data_source}</div>',unsafe_allow_html=True)
if age is not None and age>14:
    st.warning('⚠️ Results are stale. Forecasts may miss recent form; fixture dates are not independently verified.')
elif age is not None and age>7:
    st.info('Results are delayed. Confirm match schedules independently.')
if errors:st.caption('Unavailable historical seasons: '+', '.join(errors))
if len(played)<100:
    st.error('Insufficient completed matches to train the model.')
    st.stop()
with st.spinner('Fitting Dixon–Coles model…'):
    model=train_cached(played)
teams=model[0]
tab1,tab2,tab3=st.tabs(['Upcoming fixtures','Manual matchup','Historical test'])
with tab1:
    st.caption('Community-maintained fixture list · Confirm kick-off times independently.')
    if future.empty:st.info('No upcoming fixtures listed. Try manual matchup.')
    else:
        options=future.head(100).reset_index(drop=True)
        k=st.selectbox('Select fixture',range(len(options)),format_func=lambda i:f'{options.iloc[i].Date.date()} · {options.iloc[i].HomeTeam} vs {options.iloc[i].AwayTeam}')
        m=options.iloc[k]
        h=map_team(m.HomeTeam,teams)
        a=map_team(m.AwayTeam,teams)
        if h and a and h!=a:show_card(model,h,a)
        else:st.info('One team has no recorded results yet.')
with tab2:
    home=st.selectbox('Home team',teams)
    away=st.selectbox('Away team',[t for t in teams if t!=home])
    show_card(model,home,away)
with tab3:
    st.caption('80/20 chronological holdout. Historical accuracy is not betting profitability.')
    if st.button('Run historical test'):
        ordered=played.sort_values('Date').reset_index(drop=True)
        cutoff=ordered.iloc[int(len(ordered)*0.8)].Date
        train=ordered[ordered.Date<cutoff]
        test=ordered[ordered.Date>=cutoff]
        try:
            held_model=fit_dc(train)
            records=[]
            for m in test.itertuples():
                if m.HomeTeam not in held_model[0] or m.AwayTeam not in held_model[0]:continue
                _,_,g=forecast(held_model,m.HomeTeam,m.AwayTeam)
                p=np.array([np.tril(g,-1).sum(),np.trace(g),np.triu(g,1).sum()])
                outcome=0 if m.FTHG>m.FTAG else 1 if m.FTHG==m.FTAG else 2
                exact=int(np.unravel_index(np.argmax(g),g.shape)==(m.FTHG,m.FTAG))
                records.append((int(np.argmax(p)==outcome),np.mean((p-np.eye(3)[outcome])**2),-np.log(max(p[outcome],1e-12)),exact))
            if records:
                metrics=np.array(records)
                a,b,c,d=st.columns(4)
                a.metric('Test matches',len(records))
                b.metric('1X2 accuracy',f'{metrics[:,0].mean():.1%}')
                c.metric('Brier score',f'{metrics[:,1].mean():.3f}')
                d.metric('Exact score hit',f'{metrics[:,3].mean():.1%}')
                st.write(f'Log loss: {metrics[:,2].mean():.3f}')
            else:st.error('No eligible test matches.')
        except Exception as e:st.error(f'Test failed: {e}')
st.caption('Daily data: open-matchday (non-commercial use only; upstream rights apply). Historical: OpenFootball. No live scores or paid API.')
st.markdown('Attribution: [open-matchday](https://github.com/oladeeayo/open-matchday) · [OpenFootball](https://github.com/openfootball/football.json)')
