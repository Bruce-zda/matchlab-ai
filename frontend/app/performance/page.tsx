import Link from 'next/link';
type Settlement={snapshot_id:string;provider_match_id:number;model:string;league:string;actual:number;brier:number;log_loss:number};
type Forecast={snapshot_id:string;model:string;p_home:number;p_draw:number;p_away:number};
const BASE='https://raw.githubusercontent.com/Bruce-zda/matchlab-ai/main/artifacts/';
async function load<T>(name:string):Promise<T>{const r=await fetch(BASE+name,{next:{revalidate:120}});if(!r.ok)throw new Error('Feed unavailable');return r.json() as Promise<T>;}
export const metadata={title:'Performance Lab | MatchLab',description:'Auditable pre-kickoff forecast results, model scores and sample-size limitations.'};
export default async function Performance(){
 let rows:Settlement[]=[];let forecasts:Forecast[]=[];let error=false;
 try{[rows,forecasts]=await Promise.all([load<Settlement[]>('forward_settlements.json'),load<Forecast[]>('forward_ledger.json')]);}catch{error=true;}
 const byId=new Map(forecasts.map(f=>[f.snapshot_id,f]));
 const models=['Dixon-Coles','Bayesian Goals','Elo','DC + Bayesian (50/50)'];
 const summaries=models.map(model=>{const records=rows.filter(r=>r.model===model&&Number.isFinite(r.brier)&&Number.isFinite(r.log_loss)&&byId.has(r.snapshot_id));const n=records.length;
 const avg=(field:'brier'|'log_loss')=>n?records.reduce((sum,r)=>sum+r[field],0)/n:null;
 const correct=records.filter(r=>{const f=byId.get(r.snapshot_id)!;const probs=[f.p_home,f.p_draw,f.p_away];return probs.indexOf(Math.max(...probs))===r.actual;}).length;
 return {model,n,brier:avg('brier'),logLoss:avg('log_loss'),accuracy:n?correct/n:null};});
 const fixtures=new Set(rows.map(r=>r.provider_match_id)).size;
 const fmt=(n:number|null,percent=false)=>n===null?'—':percent?(n*100).toFixed(1)+'%':n.toFixed(4);
 return <main className="lab-shell"><nav className="lab-nav"><Link href="/">← Discover</Link><Link href="/methodology">Methodology →</Link></nav><div className="lab-kicker">MATCHLAB / INDEPENDENT EVIDENCE</div><h1>Performance Lab</h1><p className="lab-lead">Real, archived pre-kickoff predictions compared with recorded final results. No simulated results or invented accuracy.</p>
 {error?<section className="lab-panel"><h2>Performance feed unavailable</h2><p>We cannot verify current results. Please check again later.</p></section>:<>
 <div className="lab-stat-grid"><div className="lab-panel"><small>SETTLED FIXTURES</small><strong>{fixtures}</strong></div><div className="lab-panel"><small>MODEL SETTLEMENTS</small><strong>{rows.length}</strong></div><div className="lab-panel"><small>EVIDENCE STATUS</small><strong>Early sample</strong></div></div>
 <section className="lab-panel"><h2>Forward model comparison</h2><p>All values below use archived forecasts joined to settled results by snapshot ID. Lower Brier score and log loss are better. Accuracy is the share of correct highest-probability 1X2 outcomes.</p><div className="lab-scroll"><table className="lab-table"><thead><tr><th>Model</th><th>Settled</th><th>Top-pick accuracy</th><th>Brier ↓</th><th>Log loss ↓</th></tr></thead><tbody>{summaries.map(m=><tr key={m.model}><td>{m.model}</td><td>{m.n}</td><td>{fmt(m.accuracy,true)}</td><td>{fmt(m.brier)}</td><td>{fmt(m.logLoss)}</td></tr>)}</tbody></table></div></section>
 <section className="lab-panel lab-caution"><h2>What these results do—and don't—prove</h2><p>Small samples fluctuate substantially. Model comparisons are descriptive, not evidence of superiority, profitability, or reliable future performance. No ranking is declared until enough independent results exist. Goal-market results are not included in this 1X2 table.</p><p>Our evaluation target is at least 1,000 independently settled fixtures, followed by market-specific adequacy checks. That target is not a statistical guarantee.</p></section>
 </>}
 <footer className="lab-footer"><Link href="/">Discover matches</Link><span>Evidence over hype · MatchLab</span></footer></main>;
}
