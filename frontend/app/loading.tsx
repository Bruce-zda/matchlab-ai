export default function LoadingDiscover() {
  return <div className="lab-shell" aria-busy="true" aria-live="polite">
    <div className="skeleton skeleton-heading" />
    <div className="lab-stat-grid">
      {[0,1,2].map(i=><div key={i} className="lab-panel"><div className="skeleton skeleton-line" /><div className="skeleton skeleton-block" /></div>)}
    </div>
    <p className="loading-caption">Loading MatchLab's archived forecasts…</p>
  </div>;
}
