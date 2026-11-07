export default function LoadingMatch() {
  return <main className="detail-page" aria-busy="true" aria-live="polite">
    <div className="detail-wrap">
      <div className="skeleton skeleton-line" style={{width:160}} />
      <div className="skeleton skeleton-heading" />
      <div className="detail-panels">
        <div className="detail-panel"><div className="skeleton skeleton-line" /><div className="skeleton skeleton-heading" /><div className="skeleton skeleton-block" /></div>
        <div className="detail-panel"><div className="skeleton skeleton-line" /><div className="skeleton skeleton-block" /></div>
      </div>
      <p className="loading-caption">Loading archived match intelligence…</p>
    </div>
  </main>;
}
