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
</style>""",unsafe_allow_html=True)
st.markdown('<div class="brand"><b>MATCHLAB<span style="color:#d5ad65">.</span></b><span>FOOTBALL INTELLIGENCE / BETA</span></div>',unsafe_allow_html=True)
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
    st.markdown(f'<div class="match-card"><div class="label">MATCH CENTRE / PRE-MATCH</div><div class="fixture">{safe_home} <span style="color:#8b97a4">—</span> {safe_away}</div><div class="pick">Model lean: <b>{winner}</b> · {max(probs):.1%} estimated probability</div></div>',unsafe_allow_html=True)
    st.markdown('<div class="analysis-title">01 / Match analysis</div>',unsafe_allow_html=True)
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
    st.markdown('<div class="analysis-title">02 / What drives the forecast</div>',unsafe_allow_html=True)
    reasons=[f'The model estimates {lam:.2f} goals for {home} and {mu:.2f} for {away}, using team attacking and defensive strength plus a home advantage term.']
    if home_form and away_form:
        reasons.append(f'Across their last five recorded matches, {home} averaged {home_form["gf"]:.2f} goals scored and {away} averaged {away_form["gf"]:.2f}. These are context, not separate model inputs.')
    if home_venue and away_venue:
        reasons.append(f'At the relevant venues, {home} scored {home_venue["gf"]:.2f} per home match and {away} scored {away_venue["gf"]:.2f} per away match (up to five games each).')
    for reason in reasons:st.write(reason)
    st.caption('No verified lineups, injuries, live form feed or tactical assessment. Avoid interpreting this as a complete scouting report.')
    st.markdown('<div class="analysis-title">03 / MatchLab expert assessment</div>',unsafe_allow_html=True)
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
    # High probability alone does not establish betting value or model calibration.
    ranked_markets=sorted(markets.items(),key=lambda item:item[1],reverse=True)
    best_name,best_prob=ranked_markets[0]
    st.markdown('**Expert pick: Withheld pending independent validation**')
    st.write(f'**Highest raw model probability:** {best_name} · {best_prob:.1%}. This is a probability ranking, not a recommendation.')
    st.caption('A high probability is not proof of reliability or betting value. Early Premier League holdout results show that some goals markets underperform a simple baseline. Expert recommendations will remain disabled until per-market out-of-sample validation across leagues and time periods is complete.')
    with st.expander('Compare supported markets'):
        st.dataframe(pd.DataFrame([{'Market':name,'Model probability':f'{p:.1%}'} for name,p in ranked_markets]),hide_index=True,use_container_width=True)

    st.markdown('<div class="analysis-title">04 / Outcome probabilities</div>',unsafe_allow_html=True)
    a,b,c=st.columns(3)
    a.metric('Home',f'{probs[0]:.1%}')
    b.metric('Draw',f'{probs[1]:.1%}')
    c.metric('Away',f'{probs[2]:.1%}')
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
            archive[col]=archive[col].map(lambda x:map_team(x,current_names) or x)
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
st.markdown(f'<div class="status"><b>DATA HEALTH: {freshness}</b> · Latest recorded result: {last} · {age if age is not None else "?"} days old<br>{len(played):,} completed matches · {len(future):,} unverified upcoming fixtures</div>',unsafe_allow_html=True)
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
        if h and a and h!=a:show_card(model,h,a,played)
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
with st.expander('About the data and limitations'):
    st.caption('Daily data: open-matchday (non-commercial use only; upstream rights apply). Historical: OpenFootball. No live scores or paid API.')
    st.markdown('Attribution: [open-matchday](https://github.com/oladeeayo/open-matchday) · [OpenFootball](https://github.com/openfootball/football.json)')
