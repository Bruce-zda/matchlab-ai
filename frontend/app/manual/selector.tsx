'use client';
import {useMemo,useState} from 'react';
import Link from 'next/link';
type Forecast={snapshot_id:string;provider_match_id:number;league:string;home:string;away:string;kickoff_utc:string;captured_at_utc:string;model:string;p_home:number;p_draw:number;p_away:number};
const pct=(n:number)=>(n*100).toFixed(1)+'%';
export default function ManualExplorer({forecasts}:{forecasts:Forecast[]}){
 const leagues=useMemo(()=>[...new Set(forecasts.map(f=>f.league))].sort(),[forecasts]);
 const [league,setLeague]=useState(leagues[0]||'');
 const teams=useMemo(()=>[...new Set(forecasts.filter(f=>f.league===league).flatMap(f=>[f.home,f.away]))].sort(),[forecasts,league]);
 const [home,setHome]=useState('');
 const [away,setAway]=useState('');
 const selectedHome=teams.includes(home)?home:teams[0]||'';
 const selectedAway=teams.includes(away)&&away!==selectedHome?away:teams.find(t=>t!==selectedHome)||'';
 const matches=useMemo(()=>{const m=new Map<number,Forecast[]>();for(const f of forecasts){if(f.league!==league||f.home!==selectedHome||f.away!==selectedAway)continue;const a=m.get(f.provider_match_id)||[];a.push(f);m.set(f.provider_match_id,a);}return [...m.values()].sort((a,b)=>b[0].kickoff_utc.localeCompare(a[0].kickoff_utc));},[forecasts,league,selectedHome,selectedAway]);
 return <section className="lab-panel"><div style={{display:'flex',flexWrap:'wrap',gap:16,marginBottom:24}}>
 <label>League<br/><select aria-label="League" value={league} onChange={e=>{setLeague(e.target.value);setHome('');setAway('');}}>{leagues.map(l=><option key={l}>{l}</option>)}</select></label>
 <label>Home team<br/><select aria-label="Home team" value={selectedHome} onChange={e=>{setHome(e.target.value);if(e.target.value===selectedAway)setAway('');}}>{teams.map(t=><option key={t}>{t}</option>)}</select></label>
 <label>Away team<br/><select aria-label="Away team" value={selectedAway} onChange={e=>setAway(e.target.value)}>{teams.filter(t=>t!==selectedHome).map(t=><option key={t}>{t}</option>)}</select></label></div>
 {!forecasts.length?<p>No archived forecasts available yet.</p>:!matches.length?<p>No verified archived forecast for this home/away pairing. This tool never fabricates predictions. Try reversing the teams or choosing another pairing.</p>:matches.map(group=><article key={group[0].provider_match_id} style={{borderTop:'1px solid #344a5a',paddingTop:20,marginTop:20}}><h2>{group[0].home} vs {group[0].away}</h2><p>Kickoff: {new Date(group[0].kickoff_utc).toLocaleString('en-GB',{timeZone:'UTC',dateStyle:'medium',timeStyle:'short'})} UTC · <Link href={'/match/'+group[0].provider_match_id}>Full match analysis →</Link></p><div style={{overflowX:'auto'}}><table style={{width:'100%',textAlign:'left',borderSpacing:'12px 14px'}}><thead><tr><th>Archived model</th><th>Home</th><th>Draw</th><th>Away</th></tr></thead><tbody>{group.map(f=><tr key={f.snapshot_id}><td>{f.model}</td><td>{pct(f.p_home)}</td><td>{pct(f.p_draw)}</td><td>{pct(f.p_away)}</td></tr>)}</tbody></table></div><small>Captured before kickoff; historical snapshots only. No claim of profitability or model superiority.</small></article>)}
 </section>;
}
