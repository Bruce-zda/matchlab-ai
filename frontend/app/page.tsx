import { Activity, ArrowUpRight, BarChart3, ChevronRight, CircleDot, Clock3, ShieldCheck, Sparkles, Target, TrendingUp } from 'lucide-react';
import type { ReactNode } from 'react';

type Forecast = { snapshot_id: string; provider_match_id: number; league: string; home: string; away: string; kickoff_utc: string; captured_at_utc: string; model: string; p_home: number; p_draw: number; p_away: number };
type Settlement = { snapshot_id: string; provider_match_id: number; home_goals: number; away_goals: number; model: string };
type Match = { id: number; league: string; home: string; away: string; kickoff: string; forecasts: Forecast[]; result?: Settlement };
const BASE = 'https://raw.githubusercontent.com/Bruce-zda/matchlab-ai/main/artifacts/';
async function getJson<T>(file: string): Promise<T> {
  const response = await fetch(BASE + file, { next: { revalidate: 120 } });
  if (!response.ok) throw new Error('Unable to retrieve ' + file);
  return response.json() as Promise<T>;
}
function pct(n: number) { return (n * 100).toFixed(1) + '%'; }
function kickoff(iso: string) { return new Intl.DateTimeFormat('en-GB', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit', timeZone: 'UTC' }).format(new Date(iso)) + ' UTC'; }
function outcome(f: Forecast) { const v = [f.p_home, f.p_draw, f.p_away]; const i = v.indexOf(Math.max(...v)); return { label: [f.home + ' win', 'Draw', f.away + ' win'][i], probability: v[i], index: i }; }
function ProbBar({ f }: { f: Forecast }) { return <div className="probability"><div style={{width:pct(f.p_home)}} className="prob home" /><div style={{width:pct(f.p_draw)}} className="prob draw" /><div style={{width:pct(f.p_away)}} className="prob away" /></div>; }
function Stat({ icon, label, value, note }: {icon:ReactNode;label:string;value:string;note:string}) {return <div className="stat"><div className="stat-icon">{icon}</div><div className="stat-label">{label}</div><div className="stat-value">{value}</div><div className="stat-note">{note}</div></div>;}
function MatchCard({ match }: {match:Match}) {
 const dc = match.forecasts.find(x=>x.model==='Dixon-Coles') || match.forecasts[0];
 if (!dc) return null;
 const top = outcome(dc); const sorted = [dc.p_home,dc.p_draw,dc.p_away].sort((a,b)=>b-a);
 const margin = sorted[0]-sorted[1];
 const consensus = match.forecasts.filter(f=>outcome(f).index===top.index).length;
 return <article className="match-card" id={'match-'+match.id}>
   <div className="card-top"><span className="league-dot"/><span>{match.league}</span><span className="card-date">{kickoff(match.kickoff)}</span></div>
   <div className="teams"><div className="team">{match.home}</div><div className="versus">{match.result ? match.result.home_goals+' : '+match.result.away_goals : 'VS'}</div><div className="team team-right">{match.away}</div></div>
   <div className="prob-labels"><span>HOME <strong>{pct(dc.p_home)}</strong></span><span>DRAW <strong>{pct(dc.p_draw)}</strong></span><span>AWAY <strong>{pct(dc.p_away)}</strong></span></div>
   <ProbBar f={dc}/>
   <div className="prediction"><div><span className="eyebrow">MOST LIKELY OUTCOME</span><div className="prediction-name">{top.label}</div></div><div className="prediction-number">{pct(top.probability)}</div></div>
   <details className="intelligence"><summary><span><Sparkles size={15}/> Model intelligence</span><ChevronRight size={16}/></summary>
     <div className="intel-body"><div className="intel-grid"><div><span className="eyebrow">MODEL AGREEMENT</span><strong>{consensus} / {match.forecasts.length}</strong></div><div><span className="eyebrow">LEAD OVER RUNNER-UP</span><strong>{(margin*100).toFixed(1)} pts</strong></div></div>
     <p><strong>Statistical read:</strong> {top.label} has the highest estimated 1X2 probability. {margin<0.08?'The outcome is finely balanced.':margin<0.18?'There is a moderate statistical advantage.':'The leading outcome has a notable probability advantage.'} {consensus<match.forecasts.length?'The archived models disagree on the most likely outcome.':'All archived models favor the same outcome.'}</p>
     <div className="model-rows">{match.forecasts.map(f=><div className="model-row" key={f.snapshot_id}><span>{f.model}</span><span>{pct(f.p_home)} / {pct(f.p_draw)} / {pct(f.p_away)}</span></div>)}</div>
     <small>Probabilities are archived model estimates, not guarantees. This analysis does not claim to use unverified injuries, lineups or breaking news.</small></div>
   </details>
   <a className="open-match" href={"/match/"+match.id}>Open full match analysis <ArrowUpRight size={15}/></a>
   <div className="card-foot"><span><CircleDot size={12}/> {match.result?'Provider result recorded':'Archived pre-match forecast'}</span><span>Dixon–Coles primary</span></div>
 </article>;
}
export default async function Home({searchParams}:{searchParams:Promise<{league?:string;view?:string}>}) {
 const params = await searchParams;
 let forecasts:Forecast[]=[];let settlements:Settlement[]=[];let error=false;
 try { [forecasts,settlements]=await Promise.all([getJson<Forecast[]>('forward_ledger.json'),getJson<Settlement[]>('forward_settlements.json')]); } catch {error=true;}
 const resultMap = new Map(settlements.map(s=>[s.provider_match_id,s]));
 const grouped = new Map<number,Match>();
 for (const f of forecasts) { let m=grouped.get(f.provider_match_id);if(!m){m={id:f.provider_match_id,league:f.league,home:f.home,away:f.away,kickoff:f.kickoff_utc,forecasts:[],result:resultMap.get(f.provider_match_id)};grouped.set(f.provider_match_id,m);}m.forecasts.push(f); }
 const all=[...grouped.values()];
 const now=Date.now();
 const leagues=[...new Set(all.map(m=>m.league))].sort();
 const league=params.league||'All leagues';const view=params.view||'upcoming';
 const filtered=all.filter(m=>(league==='All leagues'||m.league===league)&&(view==='all'||(view==='results'?!!m.result:new Date(m.kickoff).getTime()>=now&&!m.result))).sort((a,b)=>view==='results'?Date.parse(b.kickoff)-Date.parse(a.kickoff):Date.parse(a.kickoff)-Date.parse(b.kickoff));
 const featured=filtered[0];const settled=new Set(settlements.map(s=>s.provider_match_id)).size;
 const href=(l:string,v:string)=>'/?league='+encodeURIComponent(l)+'&view='+v;
 return <div className="site">
 <aside className="sidebar"><a href="/" className="brand"><span className="brand-icon"><Activity size={23}/></span><span>MATCH<span className="brand-accent">LAB</span><small>FOOTBALL INTELLIGENCE</small></span></a>
 <div className="nav-heading">WORKSPACE</div><a className="nav-item active" href="/"><Target size={18}/> Discover <span className="nav-arrow">↗</span></a><a className="nav-item" href="/?view=results"><ShieldCheck size={18}/> Results archive</a><a className="nav-item" href="/performance"><BarChart3 size={18}/> Performance Lab <ArrowUpRight size={14}/></a>
 <a className="nav-item" href="/methodology"><ShieldCheck size={18}/> Methodology</a><div className="side-bottom"><div className="side-live"><span className="live-pulse"/> LIVE DATA PIPELINE</div><p>Real archived model forecasts. Independently recorded match outcomes. No invented picks.</p><div className="side-version">MATCHLAB 2.0 · PREVIEW</div></div></aside>
 <main className="main"><header className="topbar"><div className="breadcrumbs">PLATFORM <ChevronRight size={13}/> <b>DISCOVER</b></div><div className="topright"><span className="online-dot"/> Evidence-first predictions <span className="avatar">ML</span></div></header>
 <div className="content"><div className="hero"><div className="hero-glow"/><div className="hero-content"><div className="hero-tag"><Sparkles size={13}/> THE NEXT GENERATION OF MATCH INTELLIGENCE</div><h1>Read the game.<br/><em>Beyond the score.</em></h1><p>Every probability has a model behind it. Every result has a record. Explore football predictions with the context they deserve.</p><a href="#fixtures" className="hero-cta">Explore predictions <ArrowUpRight size={17}/></a></div><div className="hero-art" aria-hidden="true"><div className="orbit orbit-one"/><div className="orbit orbit-two"/><div className="orbit orbit-three"/><div className="orb-core"><Activity size={54}/></div><span className="orbit-caption">DATA → INSIGHT → DECISION</span></div></div>
 <div className="stats"><Stat icon={<Target size={18}/>} label="ARCHIVED FORECASTS" value={String(forecasts.length)} note="Immutable model snapshots"/><Stat icon={<CircleDot size={18}/>} label="TRACKED FIXTURES" value={String(all.length)} note="Across supported leagues"/><Stat icon={<ShieldCheck size={18}/>} label="SETTLED FIXTURES" value={String(settled)} note="Provider outcomes recorded"/><Stat icon={<TrendingUp size={18}/>} label="MODEL COVERAGE" value="4" note="Models per complete fixture"/></div>
 <section id="fixtures" className="fixtures"><div className="section-heading"><div><div className="section-kicker">MATCH INTELLIGENCE / 01</div><h2>Match Centre <span className="count">{filtered.length}</span></h2><p>Real predictions, clear probabilities, transparent reasoning.</p></div><div className="section-time"><Clock3 size={15}/> All times UTC</div></div>
 <div className="filters"><div className="filter-tabs"><a className={view==='upcoming'?'selected':''} href={href(league,'upcoming')}>Upcoming</a><a className={view==='results'?'selected':''} href={href(league,'results')}>Results</a><a className={view==='all'?'selected':''} href={href(league,'all')}>All archived</a></div><div className="league-filters"><a className={league==='All leagues'?'selected':''} href={href('All leagues',view)}>All leagues</a>{leagues.map(l=><a key={l} className={league===l?'selected':''} href={href(l,view)}>{l}</a>)}</div></div>
 {error?<div className="empty">Forecast feed temporarily unavailable. Please retry shortly.</div>:filtered.length===0?<div className="empty"><CircleDot size={27}/><h3>No matches in this view</h3><p>Try the All archived tab to browse published forecasts.</p><a href={href(league,'all')}>Browse archive <ArrowUpRight size={14}/></a></div>:<div className="match-grid">{filtered.slice(0,24).map(m=><MatchCard match={m} key={m.id}/>)}</div>}
 {featured&&<p className="data-note"><ShieldCheck size={15}/> All forecasts shown are from the published MatchLab ledger. Predictions are probabilistic, not certainties. Publication timing and model performance require ongoing independent audit.</p>}
 </section><footer className="footer"><span>MATCHLAB © 2026</span><span>BUILT ON EVIDENCE, NOT HYPE.</span><a href="https://github.com/Bruce-zda/matchlab-ai" target="_blank" rel="noreferrer">Open methodology <ArrowUpRight size={13}/></a></footer></div></main></div>;
}
