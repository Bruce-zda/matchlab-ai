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
