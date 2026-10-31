import datetime as dt
import io
import numpy as np
import pandas as pd
import requests
import streamlit as st
from scipy.optimize import minimize
from scipy.stats import poisson

st.set_page_config(page_title='MatchLab AI V2', page_icon='⚽', layout='wide')
st.title('⚽ MatchLab AI V2')
st.caption('Five leagues · automatic fixtures · transparent Dixon–Coles forecasts')

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
    st.subheader(f'{home} vs {away}')
    st.info(f'Most likely outcome: **{winner}** ({max(probs):.1%}). Not a certainty.')
    a,b,c=st.columns(3)
    a.metric('Home win',f'{probs[0]:.1%}')
    b.metric('Draw',f'{probs[1]:.1%}')
    c.metric('Away win',f'{probs[2]:.1%}')
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

st.warning('Research prototype, not betting advice. Community data may be incomplete or outdated.')
league=st.selectbox('Choose league',list(LEAGUES))
with st.spinner('Loading football results and fixtures…'):
    raw,errors=get_league(LEAGUES[league])
if raw.empty:
    st.error('No football records available for this league.')
    st.stop()
played=raw[(raw.Date.dt.date<TODAY)&raw.FTHG.notna()&raw.FTAG.notna()].copy()
future=raw[(raw.Date.dt.date>=TODAY)&(raw.FTHG.isna()|raw.FTAG.isna())].copy()
last=played.Date.max().date() if not played.empty else None
st.caption(f'OpenFootball data · {len(played)} completed matches · {len(future)} upcoming fixtures listed · latest result {last}')
if last and (TODAY-last).days>14:st.warning('Results may be stale; last recorded result is more than 14 days old.')
if errors:st.caption('Unavailable historical seasons: '+', '.join(errors))
if len(played)<100:
    st.error('Insufficient completed matches to train the model.')
    st.stop()
with st.spinner('Fitting Dixon–Coles model…'):
    model=train_cached(played)
teams=model[0]
tab1,tab2,tab3=st.tabs(['Upcoming fixtures','Manual matchup','Historical test'])
with tab1:
    st.caption('Community-maintained fixtures, not a verified live feed.')
    if future.empty:st.info('No upcoming fixtures listed. Try manual matchup.')
    else:
        options=future.head(100).reset_index(drop=True)
        k=st.selectbox('Select fixture',range(len(options)),format_func=lambda i:f'{options.iloc[i].Date.date()} · {options.iloc[i].HomeTeam} vs {options.iloc[i].AwayTeam}')
        m=options.iloc[k]
        if m.HomeTeam in teams and m.AwayTeam in teams:show_card(model,m.HomeTeam,m.AwayTeam)
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
st.caption('Data: OpenFootball football.json (public domain). No paid API.')
