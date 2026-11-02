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
    const [ledger, settlements, coverage] = await Promise.all([
      readArchive('forward_ledger.json'),
      readArchive('forward_settlements.json'),
      readArchive('forward_coverage.json').catch(() => null),
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
    const validCoverage = coverage && typeof coverage === 'object' && !Array.isArray(coverage) ? coverage as Record<string, unknown> : null;
    const coverageTimestamp = validCoverage && typeof validCoverage.collected_at_utc === 'string' ? Date.parse(validCoverage.collected_at_utc) : NaN;
    const coverageAgeHours = Number.isFinite(coverageTimestamp) ? Math.max(0, (Date.now() - coverageTimestamp) / 3600000) : null;
    const coverageFresh = coverageAgeHours !== null && coverageAgeHours <= 18;
    const fixtureCount = validCoverage && typeof validCoverage.fixture_count === 'number' ? validCoverage.fixture_count : null;
    const covered = validCoverage && typeof validCoverage.covered === 'number' ? validCoverage.covered : null;
    const skipped = validCoverage && typeof validCoverage.skipped === 'number' ? validCoverage.skipped : null;
    return NextResponse.json({
      status: 'ok',
      data_health: coverageFresh ? 'fresh' : 'stale_or_unavailable',
      coverage: { fixture_count: fixtureCount, covered, skipped, collected_at_utc: validCoverage?.collected_at_utc ?? null, age_hours: coverageAgeHours === null ? null : Number(coverageAgeHours.toFixed(1)), freshness_threshold_hours: 18 },
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
