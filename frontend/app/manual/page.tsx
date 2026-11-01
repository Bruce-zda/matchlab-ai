import Link from 'next/link';
import ManualExplorer from './selector';

type Forecast = { snapshot_id:string; provider_match_id:number; league:string; home:string; away:string; kickoff_utc:string; captured_at_utc:string; model:string; p_home:number; p_draw:number; p_away:number };
const BASE='https://raw.githubusercontent.com/Bruce-zda/matchlab-ai/main/artifacts/';
export const metadata={title:'Manual matchup explorer | MatchLab',description:'Compare authentic archived pre-kickoff model predictions for selected football fixtures.'};
export default async function ManualPage(){
 let rows:Forecast[]=[];let error=false;
 try {const r=await fetch(BASE+'forward_ledger.json',{next:{revalidate:120}});if(!r.ok)throw new Error('Archive unavailable');const data:unknown=await r.json();if(!Array.isArray(data))throw new Error('Unexpected archive format');rows=data.filter((x):x is Forecast=>typeof x==='object'&&x!==null&&typeof x.provider_match_id==='number'&&typeof x.snapshot_id==='string'&&typeof x.model==='string'&&typeof x.p_home==='number'&&typeof x.p_draw==='number'&&typeof x.p_away==='number'&&typeof x.home==='string'&&typeof x.away==='string'&&typeof x.league==='string'&&typeof x.kickoff_utc==='string'&&typeof x.captured_at_utc==='string');}
 catch {error=true;}
 return <main className="lab-shell"><nav className="lab-nav"><Link href="/">← Discover</Link><Link href="/performance">Performance Lab →</Link></nav><div className="lab-kicker">MATCHLAB / MANUAL EXPLORER</div><h1>Compare archived matchups</h1><p className="lab-lead">Choose a league and two teams to inspect forecasts captured before kickoff. This explorer does <b>not</b> generate new predictions or backdate estimates.</p>{error?<section className="lab-panel"><p>Forecast archive temporarily unavailable. Please retry later.</p></section>:<ManualExplorer forecasts={rows} computeEnabled={Boolean(process.env.MATCHLAB_PREVIEW_BACKEND_URL && process.env.MATCHLAB_PREVIEW_BACKEND_TOKEN)}/>}</main>;
}
