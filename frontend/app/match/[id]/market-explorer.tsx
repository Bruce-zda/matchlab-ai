'use client';

import { useMemo, useState } from 'react';

export type MarketRow = {name:string;group:string;prob:number;support:string};
const fmt=(value:number)=>(value*100).toFixed(1)+'%';

export default function MarketExplorer({rows}:{rows:MarketRow[]}){
 const [group,setGroup]=useState('All');
 const [sort,setSort]=useState<'probability'|'category'>('probability');
 const groups=useMemo(()=>['All',...Array.from(new Set(rows.map(row=>row.group)))], [rows]);
 const visible=useMemo(()=>rows.filter(row=>group==='All'||row.group===group)
   .sort((a,b)=>sort==='probability'?b.prob-a.prob:a.group.localeCompare(b.group)||b.prob-a.prob),[rows,group,sort]);
 return <div className="intelligence-explorer">
  <div className="explorer-toolbar"><div className="explorer-tabs" role="group" aria-label="Market category">
   {groups.map(item=><button type="button" key={item} aria-pressed={group===item} onClick={()=>setGroup(item)}>{item}</button>)}
  </div><label>Sort <select value={sort} onChange={e=>setSort(e.target.value as 'probability'|'category')}><option value="probability">Highest probability</option><option value="category">Category</option></select></label></div>
  <div className="explorer-grid">{visible.map(row=><article className="explorer-card" key={row.group+row.name}>
   <span>{row.group}</span><h4>{row.name}</h4><strong>{fmt(row.prob)}</strong>
   <div className="explorer-track"><div style={{width:fmt(row.prob)}}/></div>
   <small>{row.support}</small>
  </article>)}</div>
  {!visible.length&&<p>No archived probabilities available for this category.</p>}
  <p className="detail-footnote">Probability is not a guarantee or a validated recommendation. Related markets are correlated. Conditional draw-no-bet outcomes cannot be compared directly to unconditional outcomes.</p>
 </div>;
}
