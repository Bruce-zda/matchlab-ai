"""Forward evaluation ledger: pre-match immutable forecast snapshots.

A forecast is eligible only when captured before the scheduled kickoff.
This module never recalculates or rewrites a stored forecast.
"""
import datetime as dt
import hashlib
import json
import math

MODELS=('Dixon-Coles','Bayesian Goals','Elo','DC + Bayesian (50/50)')
SCHEMA_VERSION=1

def utc_time(value):
    parsed=dt.datetime.fromisoformat(str(value).replace('Z','+00:00'))
    if parsed.tzinfo is None:
        raise ValueError('Timezone required')
    return parsed.astimezone(dt.timezone.utc)

def validate_forecast(record):
    required=('league','home','away','kickoff_utc','captured_at_utc','model',
              'p_home','p_draw','p_away','model_version')
    if any(k not in record for k in required):
        raise ValueError('Missing forecast fields')
    if record['model'] not in MODELS:
        raise ValueError('Unknown model')
    if not all(isinstance(record[k],str) and record[k].strip()
               for k in ('league','home','away','model_version')):
        raise ValueError('Invalid fixture identity')
    kickoff=utc_time(record['kickoff_utc'])
    captured=utc_time(record['captured_at_utc'])
    if captured>=kickoff:
        raise ValueError('Forecast was not recorded before kickoff')
    probs=[record[k] for k in ('p_home','p_draw','p_away')]
    if any(not isinstance(x,(float,int)) or not math.isfinite(x) or x<0 or x>1 for x in probs):
        raise ValueError('Invalid probabilities')
    if abs(sum(probs)-1)>1e-6:
        raise ValueError('Probabilities must sum to one')
    if 'goal_markets' in record:
        from goal_markets import validate_goal_markets
        validate_goal_markets(record['goal_markets'])
    if 'screen_markets' in record or 'frozen_screen' in record:
        from intelligence_selection import screen_outlook
        if record['model']!='DC + Bayesian (50/50)':
            raise ValueError('Only hybrid forecasts may include frozen live screen')
        if record.get('screen_policy_version')!='intelligence_selection.screen_outlook_default_80pct_10pct_spread':
            raise ValueError('Unknown frozen screen policy version')
        markets=record.get('screen_markets')
        if not isinstance(markets,list) or not markets:
            raise ValueError('Missing frozen screen markets')
        goals=record.get('goal_markets',{}).get('markets',{})
        keys=set()
        for item in markets:
            key=item.get('key')
            if key in keys or key not in goals:
                raise ValueError('Duplicate or unsupported frozen screen market')
            keys.add(key)
            if type(item.get('probability')) not in (float,int) or abs(item['probability']-goals[key])>1e-9:
                raise ValueError('Frozen screen probability mismatch')
            spread=item.get('model_range',{}).get('spread')
            if type(spread) not in (float,int) or not math.isfinite(spread) or not 0<=spread<=1:
                raise ValueError('Invalid model disagreement')
        if record.get('frozen_screen')!=screen_outlook(markets):
            raise ValueError('Frozen screen decision mismatch')
    return True

def snapshot_id(record):
    validate_forecast(record)
    fields={k:record[k] for k in ('league','home','away','kickoff_utc','model')}
    payload=json.dumps(fields,sort_keys=True,separators=(',',':'))
    return hashlib.sha256(payload.encode()).hexdigest()[:24]

def append_snapshot(ledger,record):
    validate_forecast(record)
    identity=snapshot_id(record)
    if any(snapshot_id(existing)==identity for existing in ledger):
        raise ValueError('Forecast already recorded; immutable ledger')
    entry=dict(record)
    entry['snapshot_id']=identity
    return [*ledger,entry]

def settle_snapshot(record,home_goals,away_goals):
    validate_forecast(record)
    if any(not isinstance(g,int) or isinstance(g,bool) or g<0 for g in (home_goals,away_goals)):
        raise ValueError('Invalid final score')
    actual=0 if home_goals>away_goals else 1 if home_goals==away_goals else 2
    probs=[record[k] for k in ('p_home','p_draw','p_away')]
    return {'snapshot_id':snapshot_id(record),'actual':actual,
            'brier':sum((p-int(i==actual))**2 for i,p in enumerate(probs))/3,
            'log_loss':-math.log(max(probs[actual],1e-12))}
