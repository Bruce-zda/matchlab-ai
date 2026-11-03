import type { ReactNode } from 'react';
import { BrainCircuit, ChartNoAxesColumn, Target } from 'lucide-react';

/* All three core experiences are visible in one scrollable mobile match report.
   No hidden tabs, duplicated legacy panels or client-side state required. */
export default function MatchTabs({prediction,analysis,markets}:{prediction:ReactNode;analysis:ReactNode;markets:ReactNode}){
 return <div className="match-workspace match-report">
  <nav className="match-report-nav" aria-label="Jump to match intelligence">
   <a href="#match-prediction"><Target size={16}/> Prediction</a>
   <a href="#match-markets"><ChartNoAxesColumn size={16}/> Markets</a>
   <a href="#match-analysis"><BrainCircuit size={16}/> Analysis</a>
  </nav>
  <section id="match-prediction" className="match-report-section" aria-labelledby="match-prediction-heading">
   <h2 id="match-prediction-heading" className="match-report-heading"><Target size={19}/> Model prediction</h2>{prediction}
  </section>
  <section id="match-markets" className="match-report-section" aria-labelledby="match-markets-heading">
   <h2 id="match-markets-heading" className="match-report-heading"><ChartNoAxesColumn size={19}/> Prediction markets</h2>{markets}
  </section>
  <section id="match-analysis" className="match-report-section" aria-labelledby="match-analysis-heading">
   <h2 id="match-analysis-heading" className="match-report-heading"><BrainCircuit size={19}/> Match analysis</h2>{analysis}
  </section>
 </div>;
}
