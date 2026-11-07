import './globals.css';
import type { Metadata } from 'next';
export const metadata: Metadata = { title: 'MatchLab — Football Intelligence', description: 'Evidence-first football forecasts, model intelligence, and independently settled results.' };
export default function RootLayout({ children }: Readonly<{children: React.ReactNode}>) { return <html lang="en"><body><a href="#main-content" className="ml-skip-link">Skip to main content</a>{children}</body></html> }
