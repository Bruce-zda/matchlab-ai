import Link from 'next/link';
import { Activity, ArrowLeft, ArrowUpRight, BrainCircuit, CheckCircle2, Clock3, ShieldCheck, Target } from 'lucide-react';
import type { Metadata } from 'next';

type Forecast={snapshot_id:string;provider_match_id:number;league:string;home:string;away:string;kickoff_utc:string;captured_at_utc:string;model:string;p_home:number;p_draw:number;p_away:number};
type Settlement={snapshot_id:string;provider_match_id:number;home_goals:number;away_goals:number;model:string;actual:number};
const BASE='https://raw.githubusercontent.com/Bruce-zda/matchlab-ai/main/artifacts/';
async function read<T>(name:string):Promise<T>{const r=await fetch(BASE+name,{next:{revalidate:120}});if(!r.ok)throw Error('Data feed unavailable');return r.json() as Promise<T>}
const percent=(x:number)=>(x*100).toFixed(1)+'%';
const date=(x:string)=>new Intl.DateTimeFormat('en-GB',{dateStyle:'full',timeStyle:'short',timeZone:'UTC'}).format(new Date(x))+' UTC';
const winner=(f:Forecast)=>{const values=[f.p_home,f.p_draw,f.p_away];const i=values.indexOf(Math.max(...values));return {index:i,prob:values[i],label:[f.home+' win','Draw',f.away+' win'][i]}};
export async function generateMetadata({params}:{params:Promise<{id:string}>}):Promise<Metadata>{return {title:'Match intelligence | MatchLab',description:'Archived evidence-first football forecasts and model comparison.'}}
export default async function MatchPage({params}:{params:Promise<{id:string}>}){
 const {id}=await params;
 if(!/^\d+$/.test(id))return <main className="detail-page"><Link href="/">← Back to Discover</Link><h1>Invalid match identifier</h1></main>;
 let ledger:Forecast[];let settled:Settlement[];
 try{[ledger,settled]=await Promise.all([read<Forecast[]>('forward_ledger.json'),read<Settlement[]>('forward_settlements.json')])}catch{return <main className="detail-page"><Link href="/">← Back to Discover</Link><h1>Data temporarily unavailable</h1><p>Try again shortly.</p></main>}
 const raw=ledger.filter(x=>String(x.provider_match_id)===id).sort((a,b)=>b.captured_at_utc.localeCompare(a.captured_at_utc));
 const forecasts=Array.from(new Map(raw.slice().reverse().map(x=>[x.model,x])).values());
 if(!forecasts.length)return <main className="detail-page"><Link href="/">← Back to Discover</Link><h1>Match not found</h1><p>No archived forecasts for this fixture.</p></main>;
 const main=forecasts.find(x=>x.model==='Dixon-Coles')||forecasts[0];const top=winner(main);
 const result=settled.find(x=>x.provider_match_id===main.provider_match_id);
 const lead=[main.p_home,main.p_draw,main.p_away].sort((a,b)=>b-a);
 const margin=lead[0]-lead[1];const agree=forecasts.filter(x=>winner(x).index===top.index).length;
 const outcomes=['HOME WIN','DRAW','AWAY WIN'];
 const resultMarkets=[{name:main.home+' win',group:'Match Result',prob:main.p_home,calc:(f:Forecast)=>f.p_home},{name:'Draw',group:'Match Result',prob:main.p_draw,calc:(f:Forecast)=>f.p_draw},{name:main.away+' win',group:'Match Result',prob:main.p_away,calc:(f:Forecast)=>f.p_away}];
 const markets=[...resultMarkets,
 {name:'Home or Draw',group:'Double Chance',prob:main.p_home+main.p_draw,calc:(f:Forecast)=>f.p_home+f.p_draw},
 {name:'Home or Away',group:'Double Chance',prob:main.p_home+main.p_away,calc:(f:Forecast)=>f.p_home+f.p_away},
 {name:'Draw or Away',group:'Double Chance',prob:main.p_draw+main.p_away,calc:(f:Forecast)=>f.p_draw+f.p_away},
 {name:main.home+' (Draw No Bet)',group:'Draw No Bet',prob:main.p_home/(main.p_home+main.p_away),calc:(f:Forecast)=>f.p_home/(f.p_home+f.p_away)},
 {name:main.away+' (Draw No Bet)',group:'Draw No Bet',prob:main.p_away/(main.p_home+main.p_away),calc:(f:Forecast)=>f.p_away/(f.p_home+f.p_away)},
 ].filter(m=>Number.isFinite(m.prob));
 const ranked=markets.map(m=>({...m,agree:forecasts.filter(f=>m.calc(f)>.5).length,spread:Math.max(...forecasts.map(f=>m.calc(f)))-Math.min(...forecasts.map(f=>m.calc(f)))})).sort((a,b)=>b.agree-a.agree||a.spread-b.spread);
 const highlights=ranked.filter(m=>m.agree===forecasts.length&&m.prob>=.6).slice(0,3);
 return <main className="detail-page">
 <nav className="detail-nav"><Link href="/" className="detail-brand"><Activity size={21}/> MATCH<span>LAB</span></Link><Link href="/" className="back-link"><ArrowLeft size={16}/> Discover</Link></nav>
 <div className="detail-wrap"><div className="detail-kicker"><span className="live-pulse"/> MATCH CENTRE / {main.league.toUpperCase()}</div>
 <div className="detail-head"><div><div className="detail-meta"><Clock3 size={14}/> {date(main.kickoff_utc)} · ARCHIVED FORECAST</div><h1>{main.home}<span>vs</span>{main.away}</h1></div><div className="detail-score">{result?<><small>FINAL SCORE</small><strong>{result.home_goals} – {result.away_goals}</strong></>:<><small>FORECAST STATUS</small><strong>PRE-MATCH</strong></>}</div></div>
 <div className="detail-panels"><section className="detail-panel detail-main"><div className="detail-section-label"><Target size={17}/> FINAL MOST LIKELY PREDICTION</div><div className="detail-pick">{top.label}</div><div className="detail-prob">{percent(top.prob)} <span>model probability</span></div><div className="detail-bar"><div style={{width:percent(main.p_home),background:'#b7fb5b'}}/><div style={{width:percent(main.p_draw),background:'#f4bc61'}}/><div style={{width:percent(main.p_away),background:'#6b9ffc'}}/></div><div className="detail-triple">{[main.p_home,main.p_draw,main.p_away].map((v,i)=><div key={i}><span>{outcomes[i]}</span><strong>{percent(v)}</strong></div>)}</div><p className="detail-footnote">Dixon–Coles is the primary model. These are probabilities, not guaranteed outcomes or betting advice.</p></section>
 <section className="detail-panel detail-expert"><div className="detail-section-label"><BrainCircuit size={17}/> EXPERT MODEL READ</div><div className="detail-insight"><span>MODEL CONSENSUS</span><strong>{agree} / {forecasts.length}</strong></div><div className="detail-insight"><span>LEAD OVER SECOND OUTCOME</span><strong>{(margin*100).toFixed(1)} percentage points</strong></div><div className="detail-insight"><span>FORECAST STRENGTH</span><strong>{margin<.08?'Finely balanced':margin<.18?'Moderate edge':'Notable edge'}</strong></div><p className="detail-analysis">The primary model favors <b>{top.label}</b> with {percent(top.prob)} probability. {margin<.08?'The top two outcomes are close, so the match is difficult to separate.':margin<.18?'The favored outcome has a moderate lead over the next alternative.':'The leading outcome is meaningfully ahead of the runner-up, although uncertainty remains.'} {agree===forecasts.length?'All archived models agree on the leading outcome.':'The archived models do not unanimously agree, which adds uncertainty.'}</p></section></div>
 <section className="detail-panel market-section"><div className="detail-section-label"><Target size={17}/> MARKET INTELLIGENCE <span className="market-badge">ARCHIVED 1X2 DERIVATIONS</span></div>
 <p className="market-intro">Explore every market currently supported by our archived forecasts. Probabilities below are calculated from the same 1X2 distribution, not independent model predictions.</p>
 <h3>Top model-agreement picks <small>Not yet historically validated</small></h3>
 {highlights.length?<div className="market-highlights">{highlights.map(m=><div className="market-highlight" key={m.name}><small>{m.group}</small><strong>{m.name}</strong><b>{percent(m.prob)}</b><span>{m.agree}/{forecasts.length} models above 50% · {(m.spread*100).toFixed(1)} pp model spread</span></div>)}</div>:<p className="market-empty">No picks currently meet the full-agreement and 60% probability screening criteria.</p>}
 <h3>All supported markets</h3><div className="market-table"><div className="market-row market-row-head"><span>MARKET</span><span>OUTCOME</span><span>PRIMARY PROBABILITY</span><span>MODEL SUPPORT</span></div>{ranked.map(m=><div className="market-row" key={m.name}><span>{m.group}</span><strong>{m.name}</strong><b>{percent(m.prob)}</b><span>{m.agree}/{forecasts.length} models above 50%</span></div>)}</div>
 <div className="market-pending"><h3>Additional goal markets <small>Awaiting scoreline forecasts</small></h3><div className="market-highlights">{['Total Goals · Over / Under 1.5, 2.5, 3.5','Both Teams to Score · Yes / No','Team Goals · Home / Away totals','Correct Score · Top scorelines'].map(x=><div className="market-highlight market-unavailable" key={x}><strong>{x}</strong><span>Not available from archived 1X2 data. Goal-model distributions required.</span></div>)}</div></div><p className="detail-footnote">Draw No Bet probabilities are conditional on a non-draw result; they are not directly comparable to unconditional market probabilities. Screening measures agreement, not proven accuracy or betting value. Goals, BTTS and correct score require archived scoreline distributions and are not available yet.</p>
 </section>
 <section className="detail-panel detail-models"><div className="detail-section-label"><Activity size={17}/> FOUR-MODEL COMPARISON</div><div className="detail-table"><div className="detail-table-head"><span>MODEL</span><span>HOME</span><span>DRAW</span><span>AWAY</span><span>FAVORED</span></div>{forecasts.map(f=><div className="detail-table-row" key={f.snapshot_id}><span>{f.model}{f.model==='Dixon-Coles'&&<small> PRIMARY</small>}</span><span>{percent(f.p_home)}</span><span>{percent(f.p_draw)}</span><span>{percent(f.p_away)}</span><span>{winner(f).label}</span></div>)}</div></section>
 <div className="detail-bottom"><div><ShieldCheck size={17}/><span>Archived at {date(main.captured_at_utc)}. {result?'A provider result has been recorded.':'Result not yet settled.'} Historical prediction accuracy remains under evaluation.</span></div><Link href="/" className="detail-return">Browse more matches <ArrowUpRight size={15}/></Link></div></div></main>
}
