import io
import numpy as np
import pandas as pd
import requests
import streamlit as st
from scipy.optimize import minimize
from scipy.stats import poisson

st.set_page_config(page_title='MatchLab AI', page_icon='⚽', layout='wide')
st.title('⚽ MatchLab AI')
st.caption('Transparent football forecasts • Dixon–Coles baseline • not betting advice')

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

st.info('Upload a legally usable historical results CSV. This app does not download third-party datasets automatically.')
file=st.file_uploader('Historical match CSV',type=['csv'])
if not file:
    st.write('Required columns: `Date`, `HomeTeam`, `AwayTeam`, `FTHG`, `FTAG`. Include at least 100 completed matches from one competition. Dates should be day-first.')
    st.stop()
try: data=load_csv(file)
except Exception as e:st.error(str(e));st.stop()
if len(data)<100:st.error('Please provide at least 100 valid historical matches.');st.stop()

st.sidebar.header('Controls')
cutoff=st.sidebar.date_input('Training data through',value=data.Date.max().date(),min_value=data.Date.min().date(),max_value=data.Date.max().date())
train=data[data.Date.dt.date<=cutoff].copy()
if len(train)<100:st.error('Training window needs at least 100 matches.');st.stop()
half_life=st.sidebar.slider('Recency half-life (days)',120,900,365,30)
with st.spinner('Fitting Dixon–Coles model…'):
    model=fit_dc(train,half_life)
teams=model[0]
st.success(f'Model trained on {len(train):,} matches through {train.Date.max().date()} • {len(teams)} teams')

tab1,tab2=st.tabs(['🔎 Select matchup','📅 Fixtures from uploaded CSV'])
with tab1:
    col1,col2=st.columns(2)
    home=col1.selectbox('Home team',teams)
    away=col2.selectbox('Away team',[t for t in teams if t!=home])
with tab2:
    future=data[(data.Date.dt.date>cutoff)&data.HomeTeam.isin(teams)&data.AwayTeam.isin(teams)]
    st.caption('Fixtures shown here are only rows in your uploaded CSV after the training cutoff. Their results are hidden until evaluation; this is not a live fixture feed.')
    if future.empty:st.write('No future rows found in the uploaded CSV. Live fixtures require a separately licensed API.')
    else:
        labels=[f'{r.Date.date()} | {r.HomeTeam} vs {r.AwayTeam}' for r in future.itertuples()]
        selection=st.selectbox('Select a held-out fixture',range(len(labels)),format_func=lambda i:labels[i])
        if st.button('Analyse selected fixture'):
            row=future.iloc[selection];st.session_state['fixture']=(row.HomeTeam,row.AwayTeam)
if 'fixture' in st.session_state:
    home,away=st.session_state['fixture']
    st.caption('Using selected fixture; choose a new matchup in the selector to switch.')
lam,mu,grid=forecast(model,home,away)
probs=[float(np.tril(grid,-1).sum()),float(np.trace(grid)),float(np.triu(grid,1).sum())]
st.subheader(f'{home} vs {away}')
a,b,c=st.columns(3)
a.metric('Home win',f'{probs[0]:.1%}')
b.metric('Draw',f'{probs[1]:.1%}')
c.metric('Away win',f'{probs[2]:.1%}')
st.write(f'**Expected goals:** {home} {lam:.2f} — {mu:.2f} {away}')
under=float(sum(grid[i,j] for i in range(grid.shape[0]) for j in range(grid.shape[1]) if i+j<=2))
btts=float(grid[1:,1:].sum())
st.write(f'**Over 2.5:** {1-under:.1%} · **Under 2.5:** {under:.1%} · **Both teams score:** {btts:.1%}')
ranked=sorted(((i,j,float(grid[i,j])) for i in range(grid.shape[0]) for j in range(grid.shape[1])),key=lambda x:x[2],reverse=True)[:3]
st.write('**Top 3 exact scores:** '+ ' · '.join(f'{i}–{j} ({p:.1%})' for i,j,p in ranked))
st.caption('Probabilities are model estimates, not guarantees. The finite score grid is renormalized. No independent validation or profitability claim is made.')

st.divider()
st.subheader('🧪 Chronological holdout evaluation')
st.write('To evaluate without leakage, choose an earlier training cutoff in the sidebar. All later matches in the uploaded CSV become the holdout set.')
held=data[(data.Date.dt.date>cutoff)&data.HomeTeam.isin(teams)&data.AwayTeam.isin(teams)]
if held.empty:st.info('No holdout matches. Move the training cutoff earlier to enable testing.')
else:
    records=[]
    for row in held.itertuples():
        _,_,g=forecast(model,row.HomeTeam,row.AwayTeam)
        p=np.array([np.tril(g,-1).sum(),np.trace(g),np.triu(g,1).sum()])
        actual=0 if row.FTHG>row.FTAG else 1 if row.FTHG==row.FTAG else 2
        records.append({'Date':row.Date.date(),'Match':f'{row.HomeTeam}–{row.AwayTeam}', 'Actual': ['H','D','A'][actual], 'Prediction':['H','D','A'][int(p.argmax())], 'P(H)':p[0],'P(D)':p[1],'P(A)':p[2], 'Correct':int(p.argmax()==actual),'Brier':float(np.sum((p-np.eye(3)[actual])**2)/3),'Log loss':float(-np.log(max(p[actual],1e-12))), 'Exact score hit':int(np.argmax(g)==row.FTHG*g.shape[1]+row.FTAG)})
    results=pd.DataFrame(records)
    x,y,z,w=st.columns(4)
    x.metric('1X2 accuracy',f'{results.Correct.mean():.1%}')
    y.metric('Brier score ↓',f'{results.Brier.mean():.3f}')
    z.metric('Log loss ↓',f'{results["Log loss"].mean():.3f}')
    w.metric('Exact-score hit rate',f'{results["Exact score hit"].mean():.1%}')
    st.caption(f'{len(results)} holdout matches • fixed model trained only before the cutoff • no retraining during holdout')
    st.dataframe(results,hide_index=True,use_container_width=True)
    st.download_button('Download evaluation CSV',results.to_csv(index=False).encode(),'matchlab_holdout.csv','text/csv')
