'use client';

import { useState, type ReactNode } from 'react';
import { BrainCircuit, ChartNoAxesColumn, Target } from 'lucide-react';

type Tab='prediction'|'analysis'|'markets';
export default function MatchTabs({prediction,analysis,markets}:{prediction:ReactNode;analysis:ReactNode;markets:ReactNode}){
 const [active,setActive]=useState<Tab>('prediction');
 const tabs:[Tab,string,ReactNode][]=[
  ['prediction','Prediction',<Target size={17} key="prediction"/>],
  ['analysis','Analysis',<BrainCircuit size={17} key="analysis"/>],
  ['markets','Markets',<ChartNoAxesColumn size={17} key="markets"/>],
 ];
 return <div className="match-workspace">
  <div className="match-tabbar" role="tablist" aria-label="Match centre sections">
   {tabs.map(([key,label,icon])=><button key={key} id={'match-tab-'+key} type="button" role="tab" aria-selected={active===key} aria-controls={'match-panel-'+key} tabIndex={active===key?0:-1} onClick={()=>setActive(key)} onKeyDown={e=>{if(e.key!=='ArrowLeft'&&e.key!=='ArrowRight')return;e.preventDefault();const next=tabs[(tabs.findIndex(t=>t[0]===active)+(e.key==='ArrowRight'?1:tabs.length-1))%tabs.length][0];setActive(next);requestAnimationFrame(()=>document.getElementById('match-tab-'+next)?.focus());}}>{icon}<span>{label}</span></button>)}
  </div>
  <section id="match-panel-prediction" role="tabpanel" aria-labelledby="match-tab-prediction" hidden={active!=='prediction'}>{prediction}</section>
  <section id="match-panel-analysis" role="tabpanel" aria-labelledby="match-tab-analysis" hidden={active!=='analysis'}>{analysis}</section>
  <section id="match-panel-markets" role="tabpanel" aria-labelledby="match-tab-markets" hidden={active!=='markets'}>{markets}</section>
 </div>;
}
