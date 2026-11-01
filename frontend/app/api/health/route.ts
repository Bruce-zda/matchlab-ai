import { NextResponse } from 'next/server';

export const dynamic = 'force-dynamic';

const BASE = 'https://raw.githubusercontent.com/Bruce-zda/matchlab-ai/main/artifacts/';

async function readArchive(name: string): Promise<unknown> {
  const response = await fetch(BASE + name, { cache: 'no-store', signal: AbortSignal.timeout(10000) });
  if (!response.ok) throw new Error(name + ' returned HTTP ' + response.status);
  return response.json();
}

export async function GET() {
  try {
    const [ledger, settlements] = await Promise.all([
      readArchive('forward_ledger.json'),
      readArchive('forward_settlements.json'),
    ]);
    if (!Array.isArray(ledger) || !Array.isArray(settlements)) {
      throw new Error('Archive schema must contain arrays');
    }
    if (ledger.length === 0) throw new Error('Forecast archive is empty');
    const seen = new Set<string>();
    for (const item of ledger) {
      if (!item || typeof item !== 'object') throw new Error('Malformed forecast record');
      const record = item as Record<string, unknown>;
      if (typeof record.snapshot_id !== 'string' || seen.has(record.snapshot_id)) {
        throw new Error('Missing or duplicate forecast snapshot ID');
      }
      seen.add(record.snapshot_id);
      for (const key of ['p_home', 'p_draw', 'p_away']) {
        if (typeof record[key] !== 'number' || !Number.isFinite(record[key]) || record[key] < 0 || record[key] > 1) {
          throw new Error('Invalid forecast probability');
        }
      }
      const sum = (record.p_home as number) + (record.p_draw as number) + (record.p_away as number);
      if (Math.abs(sum - 1) > 1e-5) throw new Error('Forecast probabilities do not sum to one');
    }
    const settledIds = new Set<string>();
    for (const item of settlements) {
      if (!item || typeof item !== 'object') throw new Error('Malformed settlement record');
      const record = item as Record<string, unknown>;
      if (typeof record.snapshot_id !== 'string' || !seen.has(record.snapshot_id) || settledIds.has(record.snapshot_id)) {
        throw new Error('Settlement is orphaned, missing ID, or duplicated');
      }
      settledIds.add(record.snapshot_id);
    }
    return NextResponse.json({
      status: 'ok',
      source: 'verified-repository-archive',
      archived_forecasts: ledger.length,
      settled_forecasts: settlements.length,
      checked_at_utc: new Date().toISOString(),
    }, { headers: { 'Cache-Control': 'no-store' } });
  } catch (error) {
    return NextResponse.json({
      status: 'degraded',
      reason: error instanceof Error ? error.message : 'Unknown archive error',
      checked_at_utc: new Date().toISOString(),
    }, { status: 503, headers: { 'Cache-Control': 'no-store' } });
  }
}
