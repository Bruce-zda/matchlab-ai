import { NextRequest, NextResponse } from 'next/server';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

const LEAGUES = new Set(['Premier League', 'La Liga', 'Serie A', 'Bundesliga', 'Ligue 1']);
const hits = new Map<string, number[]>();
const LIMIT = 3;
const WINDOW = 60 * 60 * 1000;

function response(message: string, status: number) {
  return NextResponse.json({ error: message }, { status, headers: { 'Cache-Control': 'no-store' } });
}

export async function POST(request: NextRequest) {
  const backend = process.env.MATCHLAB_PREVIEW_BACKEND_URL;
  const secret = process.env.MATCHLAB_PREVIEW_BACKEND_TOKEN;
  if (!backend || !secret) return response('On-demand compute is not configured. Archived comparisons remain available.', 503);
  let parsed: URL;
  try { parsed = new URL(backend); } catch { return response('Preview backend configuration invalid.', 503); }
  if (parsed.protocol !== 'https:' || parsed.username || parsed.password || parsed.search || parsed.hash || parsed.pathname !== '/preview') return response('Preview backend must use HTTPS.', 503);

  const origin = request.headers.get('origin');
  if (origin && origin !== request.nextUrl.origin) return response('Cross-origin requests are not accepted.', 403);
  const length = Number(request.headers.get('content-length') || '0');
  if (length > 2048) return response('Request too large.', 413);
  let payload: unknown;
  try { payload = await request.json(); } catch { return response('Invalid JSON.', 400); }
  if (!payload || typeof payload !== 'object' || Array.isArray(payload)) return response('Invalid request.', 400);
  const data = payload as Record<string, unknown>;
  const league = data.league, home = data.home, away = data.away, kickoff = data.kickoff_utc;
  if (typeof league !== 'string' || !LEAGUES.has(league) ||
      typeof home !== 'string' || typeof away !== 'string' ||
      home.length > 100 || away.length > 100 || !home.trim() || !away.trim() ||
      home.trim().toLowerCase() === away.trim().toLowerCase() ||
      typeof kickoff !== 'string' || kickoff.length > 40 ||
      !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?(?:Z|\+00:00)$/.test(kickoff)) {
    return response('Select valid, distinct teams, a supported league and an independently verified UTC kickoff.', 400);
  }
  const start = Date.parse(kickoff);
  if (!Number.isFinite(start) || start <= Date.now() || start > Date.now() + 14 * 86400000) {
    return response('Kickoff must be within the next 14 days.', 400);
  }
  // Per-instance throttling is defense in depth, not a distributed rate limiter.
  const key = (request.headers.get('x-forwarded-for') || 'unknown').split(',')[0].trim();
  const now = Date.now();
  if (hits.size > 2000) hits.clear();
  const recent = (hits.get(key) || []).filter(t => now - t < WINDOW);
  if (recent.length >= LIMIT) return response('Preview limit reached. Try again later.', 429);
  recent.push(now); hits.set(key, recent);
  try {
    const upstream = await fetch(parsed.toString(), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: 'Bearer ' + secret },
      body: JSON.stringify({ league, home: home.trim(), away: away.trim(), kickoff_utc: kickoff }),
      signal: AbortSignal.timeout(25000),
      cache: 'no-store',
    });
    if (!upstream.ok) return response('Prediction compute unavailable. Try again later.', 502);
    const result: unknown = await upstream.json();
    if (!result || typeof result !== 'object' || Array.isArray(result)) return response('Unexpected compute response.', 502);
    const preview = result as Record<string, unknown>;
    if (preview.kind !== 'on_demand_preview' || preview.official_forward_archive !== false || preview.fixture_verified !== true ||
        !Array.isArray(preview.forecasts) || preview.forecasts.length !== 4) return response('Invalid preview response.', 502);
    return NextResponse.json(preview, { headers: { 'Cache-Control': 'no-store' } });
  } catch { return response('Prediction compute timed out or unavailable.', 502); }
}
