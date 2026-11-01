import './globals.css';
import type { Metadata } from 'next';
export const metadata: Metadata = { title: 'MatchLab — Football Intelligence', description: 'Evidence-first football forecasts, model intelligence, and independently settled results.' };
export default function RootLayout({ children }: Readonly<{children: React.ReactNode}>) { return <html lang="en"><body>{children}</body></html> }
