"""Paired model score differences on shared settled fixtures."""
from collections import defaultdict


def compare(ledger, settlements):
    sources = {r['snapshot_id']: r for r in ledger}
    grouped = defaultdict(dict)
    for row in settlements:
        source = sources.get(row['snapshot_id'])
        if source is None or source.get('provider_match_id') != row['provider_match_id']:
            raise ValueError('Settlement identity mismatch')
        fid = row['provider_match_id']
        if row['model'] in grouped[fid]:
            raise ValueError('Duplicate model for fixture')
        grouped[fid][row['model']] = (source, row)
    paired = []
    for fid, models in grouped.items():
        if 'Dixon-Coles' not in models or 'DC + Bayesian (50/50)' not in models:
            continue
        a, base = models['Dixon-Coles']
        b, hybrid = models['DC + Bayesian (50/50)']
        if base['actual'] != hybrid['actual'] or a['kickoff_utc'] != b['kickoff_utc']:
            raise ValueError('Inconsistent fixture outcomes')
        paired.append({'fixture_id': fid, 'league': a['league'],
                       'month': a['kickoff_utc'][:7],
                       'brier_delta': hybrid['brier'] - base['brier'],
                       'log_loss_delta': hybrid['log_loss'] - base['log_loss']})
    return paired


def uncertainty(paired, repetitions=1000, seed=1729):
    """Resample league-month blocks; descriptive, not a promotion decision."""
    import random
    if not paired:
        return None
    if repetitions < 40:
        raise ValueError('At least 40 bootstrap repetitions required')
    blocks = defaultdict(list)
    for row in paired:
        blocks[(row['league'], row['month'])].append(row)
    groups = list(blocks.values())
    rng = random.Random(seed)
    samples = {'brier_delta': [], 'log_loss_delta': []}
    for _ in range(repetitions):
        drawn = [row for _ in groups for row in rng.choice(groups)]
        for metric in samples:
            samples[metric].append(sum(row[metric] for row in drawn) / len(drawn))
    output = {}
    for metric, values in samples.items():
        values.sort()
        output[metric] = [values[int(0.025 * (repetitions - 1))],
                          values[int(0.975 * (repetitions - 1))]]
    return output
