"""Settle immutable pre-match forecasts using provider fixture IDs only."""
import collections
import datetime as dt
import json
import pathlib
import sys

ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from forward_validation import settle_snapshot,snapshot_id,utc_time
from football_data_provider import finished_scores

def reconcile(ledger,provider_matches,previous=None):
    previous=previous or []
    scores=finished_scores(provider_matches)
    by_id={}
    conflicting=set()
    for score in scores:
        key=score['provider_match_id']
        if not isinstance(key,int):
            continue
        if key in by_id and by_id[key]!=(score['home_goals'],score['away_goals']):
            conflicting.add(key)
        by_id[key]=(score['home_goals'],score['away_goals'])
    for key in conflicting:
        del by_id[key]
    existing={row['snapshot_id']:row for row in previous}
    if len(existing)!=len(previous):
        raise ValueError('Duplicate settlement snapshot IDs')
    settled=list(previous)
    audit={'total_snapshots':len(ledger),'newly_settled':0,'already_settled':0,
           'awaiting_verified_result':0,'conflicting_provider_results':len(conflicting)}
    for record in ledger:
        sid=snapshot_id(record)
        if record.get('snapshot_id')!=sid:
            raise ValueError('Corrupt forecast snapshot ID')
        match_id=record.get('provider_match_id')
        if not isinstance(match_id,int) or match_id not in by_id:
            audit['awaiting_verified_result']+=1
            continue
        hg,ag=by_id[match_id]
        outcome=settle_snapshot(record,hg,ag)
        outcome.update({'provider_match_id':match_id,'home_goals':hg,'away_goals':ag,
                        'model':record['model'],'league':record['league']})
        if sid in existing:
            if existing[sid]!=outcome:
                raise ValueError('Previously published settlement differs from current result; manual review required')
            audit['already_settled']+=1
        else:
            settled.append(outcome)
            audit['newly_settled']+=1
    return settled,audit

def summary(ledger,settlements):
    by_snapshot={r['snapshot_id']:r for r in ledger}
    groups=collections.defaultdict(list)
    for row in settlements:
        forecast=by_snapshot.get(row['snapshot_id'])
        if forecast is None:
            raise ValueError('Settlement without forecast')
        groups[row['model']].append(row)
    return {'status':'pilot_forward_results_not_validated','settled_forecasts':len(settlements),
            'settled_fixtures':len({r['provider_match_id'] for r in settlements}),
            'models':[{'model':model,'n':len(rows),
                       'mean_brier':sum(r['brier'] for r in rows)/len(rows),
                       'mean_log_loss':sum(r['log_loss'] for r in rows)/len(rows)}
                      for model,rows in sorted(groups.items())]}

def main():
    if len(sys.argv)!=4:
        raise SystemExit('Usage: python scripts/settle_forward.py ledger.json matches.json settlements.json')
    ledger_path,matches_path,out_path=map(pathlib.Path,sys.argv[1:])
    ledger=json.loads(ledger_path.read_text())
    matches=json.loads(matches_path.read_text())
    previous=json.loads(out_path.read_text()) if out_path.exists() else []
    settled,audit=reconcile(ledger,matches,previous)
    candidate=out_path.with_name(out_path.stem+'.candidate.json')
    candidate.write_text(json.dumps(settled,indent=2)+'\n')
    report=summary(ledger,settled)
    (ROOT/'artifacts'/'forward_results_report.json').write_text(json.dumps(
        {'audit':audit,**report},indent=2)+'\n')
    print(json.dumps({'audit':audit,'report':report},indent=2))

if __name__=='__main__':
    main()
