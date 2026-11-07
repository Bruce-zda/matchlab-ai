'use client';
import { useMemo, useState } from 'react';
export type MarketRow={name:string;group:string;prob:number;support:string};
const fmt=(value:number)=>(value*100).toFixed(1)+'%';
export default function MarketExplorer({rows}:{rows:MarketRow[]}){
 const [group,setGroup]=useState('All markets');
 const [expanded,setExpanded]=useState<string|null>(null);
 const [sort,setSort]=useState<'probability'|'category'>('category');
 const comparable=(r:MarketRow)=>r.group!=='Draw No Bet'&&r.group!=='Asian Handicap';
 const groups=useMemo(()=>['All markets',...new Set(rows.map(r=>r.group))],[rows]);
 const visible=useMemo(()=>rows.filter(r=>Number.isFinite(r.prob)&&r.prob>=0&&r.prob<=1&&(group==='All markets'||r.group===group)).sort((a,b)=>sort==='probability'?(comparable(a)===comparable(b)?b.prob-a.prob:comparable(a)?-1:1):a.group.localeCompare(b.group)||b.prob-a.prob),[rows,group,sort]);
 const top=visible.filter(comparable).reduce<(typeof visible)[number]|undefined>((best,row)=>!best||row.prob>best.prob?row:best,undefined);
 return <div className="ml-market-browser">
  <div className="ml-market-summary"><div><span>PREDICTION MARKETS</span><strong>{rows.length}</strong><small>Available probability estimates</small></div><div><span>CURRENT VIEW</span><strong>{visible.length}</strong><small>{group}</small></div></div>
  <div className="ml-market-filter" role="group" aria-label="Filter prediction markets">{groups.map(item=><button type="button" key={item} className={group===item?'selected':''} aria-pressed={group===item} onClick={()=>setGroup(item)}>{item}</button>)}</div>
  <div className="ml-market-sort"><span>{visible.length} outcomes</span><label>Order by <select value={sort} onChange={e=>setSort(e.target.value as 'probability'|'category')}><option value="probability">Probability (comparable first)</option><option value="category">Market category</option></select></label></div>
  {top&&<div className="ml-market-feature"><small>HIGHEST ESTIMATE IN CURRENT VIEW</small><div><h3>{top.name}</h3><strong>{fmt(top.prob)}</strong></div><div className="ml-market-track"><span style={{width:fmt(top.prob)}}/></div><p>{top.group} · {top.support}. Conditional and push-sensitive markets are excluded from this comparison. Different outcomes may overlap, and a high estimate does not prove accuracy or betting value.</p></div>}
  <div className="ml-market-list ml-market-list-premium">{visible.map(row=>{const key=row.group+row.name;const open=expanded===key;return <article key={key} className="ml-market-line"><button type="button" className="ml-market-row-button" aria-expanded={open} onClick={()=>setExpanded(open?null:key)}><span className="ml-market-row-name"><small>{row.group}{!comparable(row)?' · SPECIAL SETTLEMENT':''}</small><strong>{row.name}</strong></span><span className="ml-market-row-prob">{fmt(row.prob)}</span><span className="ml-market-row-toggle" aria-hidden="true">{open?'−':'+'}</span></button>{open&&<div className="ml-market-row-context"><div className="ml-market-track"><span style={{width:fmt(row.prob)}}/></div><p>{row.support}</p></div>}</article>})}</div>
  {!visible.length&&<div className="ml-market-empty">No published probabilities are available in this category. We don't generate substitute numbers.</div>}
  <details className="ml-market-method-note"><summary>Important notes about market probabilities</summary><p>Markets derived from the same scoreline distribution are correlated. Draw No Bet probabilities are conditional on no draw. Asian Handicap win probabilities can include a push outcome. Neither is directly comparable with an unconditional win probability; they are shown separately in ranking and never used as the overall highest-probability feature.</p></details>
 </div>
}
