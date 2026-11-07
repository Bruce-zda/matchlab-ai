'use client';
import { useState, type ReactNode } from 'react';
import { Activity, BrainCircuit, ChartNoAxesColumn, Target, Users } from 'lucide-react';
type Section='overview'|'predictions'|'statistics'|'h2h'|'analysis';
export default function MatchTabs({prediction,analysis,markets,statistics,h2h}:{prediction:ReactNode;analysis:ReactNode;markets:ReactNode;statistics:ReactNode;h2h:ReactNode}){
 const [active,setActive]=useState<Section>('overview');
 const sections:[Section,string,ReactNode,ReactNode][]=[
 ['overview','Overview',<Target size={16} key="overview"/>,prediction],
 ['predictions','Predictions',<ChartNoAxesColumn size={16} key="predictions"/>,markets],
 ['statistics','Statistics',<Activity size={16} key="statistics"/>,statistics],
 ['h2h','H2H',<Users size={16} key="h2h"/>,h2h],
 ['analysis','Analysis',<BrainCircuit size={16} key="analysis"/>,analysis]
 ];
 return <div className="match-workspace ml-tab-experience premium-match-tabs ml-match-centre">
 <div className="ml-tab-navigation" role="tablist" aria-label="Match centre sections">
 {sections.map(([id,label,icon])=><button type="button" key={id} id={'ml-tab-'+id} role="tab" aria-controls={'ml-panel-'+id} aria-selected={active===id} tabIndex={active===id?0:-1} className={active===id?'active':''} onClick={()=>setActive(id)} onKeyDown={e=>{if(!['ArrowRight','ArrowLeft','Home','End'].includes(e.key))return;e.preventDefault();const i=sections.findIndex(s=>s[0]===active);const next=e.key==='Home'?sections[0][0]:e.key==='End'?sections[sections.length-1][0]:sections[(i+(e.key==='ArrowRight'?1:sections.length-1))%sections.length][0];setActive(next);requestAnimationFrame(()=>document.getElementById('ml-tab-'+next)?.focus());}}>{icon}<span>{label}</span></button>)}
 </div>
 {sections.map(([id,label,icon,content])=><section key={id} id={'ml-panel-'+id} role="tabpanel" aria-labelledby={'ml-tab-'+id} hidden={active!==id} className="ml-tab-panel"><h2 className="ml-tab-title">{icon}<span>{label==='Overview'?'Match overview':label==='Predictions'?'Prediction markets':label==='Statistics'?'Team statistics':label==='H2H'?'Head-to-head history':'Football analysis'}</span></h2>{content}</section>)}
 </div>;
}
