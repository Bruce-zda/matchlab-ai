'use client';
import { useMemo, useState } from 'react';
export type MarketRow={name:string;group:string;prob:number;support:string};
const fmt=(value:number)=>(value*100).toFixed(1)+'%';
export default function MarketExplorer({rows}:{rows:MarketRow[]}){
 const [group,setGroup]=useState('All markets');
 const [sort,setSort]=useState<'probability'|'category'>('category');
 const groups=useMemo(()=>['All markets',...new Set(rows.map(r=>r.group))],[rows]);
 const visible=useMemo(()=>rows.filter(r=>Number.isFinite(r.prob)&&r.prob>=0&&r.prob<=1&&(group==='All markets'||r.group===group)).sort((a,b)=>sort==='probability'?b.prob-a.prob:a.group.localeCompare(b.group)||b.prob-a.prob),[rows,group,sort]);
 const top=visible.reduce<(typeof visible)[number]|undefined>((best,row)=>!best||row.prob>best.prob?row:best,undefined);
 return <div className="ml-market-browser">
  <div className="ml-market-summary"><div><span>PREDICTION MARKETS</span><strong>{rows.length}</strong><small>Available probability estimates</small></div><div><span>CURRENT VIEW</span><strong>{visible.length}</strong><small>{group}</small></div></div>
  <div className="ml-market-filter" role="group" aria-label="Filter prediction markets">{groups.map(item=><button type="button" key={item} className={group===item?'selected':''} aria-pressed={group===item} onClick={()=>setGroup(item)}>{item}</button>)}</div>
  <div className="ml-market-sort"><span>{visible.length} outcomes</span><label>Order by <select value={sort} onChange={e=>setSort(e.target.value as 'probability'|'category')}><option value="probability">Probability</option><option value="category">Market category</option></select></label></div>
  {top&&<div className="ml-market-feature"><small>HIGHEST ESTIMATED PROBABILITY</small><div><h3>{top.name}</h3><strong>{fmt(top.prob)}</strong></div><div className="ml-market-track"><span style={{width:fmt(top.prob)}}/></div><p>{top.group} · {top.support}. Probability is not the same as betting value or proven accuracy.</p></div>}
  <div className="ml-market-list ml-market-list-premium">{visible.map(row=><article key={row.group+row.name} className="ml-market-line"><div className="ml-market-line-top"><div><small>{row.group}</small><h4>{row.name}</h4></div><strong>{fmt(row.prob)}</strong></div><div className="ml-market-track"><span style={{width:fmt(row.prob)}}/></div><details className="ml-market-detail"><summary>How this estimate was calculated</summary><p>{row.support}</p></details></article>)}</div>
  {!visible.length&&<div className="ml-market-empty">No published probabilities are available in this category. We don't generate substitute numbers.</div>}
  <details className="ml-market-method-note"><summary>Important notes about market probabilities</summary><p>Markets derived from the same scoreline distribution are correlated. Draw No Bet is conditional on a non-draw; it should not be ranked against unconditional probabilities as though they were equivalent.</p></details>
 </div>
}
