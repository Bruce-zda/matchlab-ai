'use client';
import { useState, type ReactNode } from 'react';
import { BrainCircuit, ChartNoAxesColumn, Target } from 'lucide-react';
type Section='prediction'|'markets'|'analysis';
export default function MatchTabs({prediction,analysis,markets}:{prediction:ReactNode;analysis:ReactNode;markets:ReactNode}){
 const [active,setActive]=useState<Section>('prediction');
 const sections:[Section,string,ReactNode,ReactNode][]=[
  ['prediction','Prediction',<Target size={16} key="prediction"/>,prediction],
  ['markets','Markets',<ChartNoAxesColumn size={16} key="markets"/>,markets],
  ['analysis','Analysis',<BrainCircuit size={16} key="analysis"/>,analysis]
 ];
 return <div className="match-workspace ml-tab-experience">
  <div className="ml-tab-navigation" role="tablist" aria-label="Match intelligence sections">
   {sections.map(([id,label,icon])=><button type="button" key={id} id={'ml-tab-'+id} role="tab" aria-controls={'ml-panel-'+id} aria-selected={active===id} tabIndex={active===id?0:-1} className={active===id?'active':''} onClick={()=>setActive(id)} onKeyDown={e=>{if(e.key!=='ArrowRight'&&e.key!=='ArrowLeft')return;e.preventDefault();const i=sections.findIndex(s=>s[0]===active);const next=sections[(i+(e.key==='ArrowRight'?1:sections.length-1))%sections.length][0];setActive(next);requestAnimationFrame(()=>document.getElementById('ml-tab-'+next)?.focus());}}>{icon}<span>{label}</span></button>)}
  </div>
  {sections.map(([id,label,icon,content])=><section key={id} id={'ml-panel-'+id} role="tabpanel" aria-labelledby={'ml-tab-'+id} hidden={active!==id} className="ml-tab-panel"><h2 className="ml-tab-title">{icon}<span>{label==='Prediction'?'Match prediction':label==='Markets'?'Market probabilities':'Football analysis'}</span></h2>{content}</section>)}
 </div>;
}
