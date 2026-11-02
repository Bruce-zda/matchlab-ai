'use client';

import { useEffect } from 'react';
import Link from 'next/link';

export default function MatchError({error,reset}:{error:Error & {digest?:string};reset:()=>void}) {
  useEffect(()=>{console.error('Match Centre failed to render',error);},[error]);
  return <main className="detail-page"><div className="detail-wrap">
    <p className="detail-kicker">MATCHLAB / MATCH CENTRE</p>
    <h1>We couldn't load this match.</h1>
    <p className="detail-footnote">Your archived predictions haven't been changed. Please try again.</p>
    <div className="error-actions"><button type="button" onClick={reset}>Try again</button><Link href="/">Back to Discover</Link></div>
  </div></main>;
}
