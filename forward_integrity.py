"""Tamper-evident digest over the full published forecast ledger.

The manifest is committed beside the ledger. Git history is the independent
timestamped evidence; a digest alone does not establish pre-kickoff publication.
"""
import hashlib
import json

def ledger_digest(records):
    if not isinstance(records,list):
        raise ValueError('Expected ledger list')
    payload=json.dumps(records,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False)
    return hashlib.sha256(payload.encode('utf-8')).hexdigest()

def manifest(records):
    return {'schema_version':1,'record_count':len(records),
            'sha256':ledger_digest(records),
            'scope':'complete_ordered_forecast_records',
            'note':'Verify against the forecast ledger in the same Git commit; Git commit history supplies publication evidence.'}

def verify(records,proof):
    expected=manifest(records)
    if not isinstance(proof,dict) or any(proof.get(k)!=v for k,v in expected.items()):
        raise ValueError('Forecast manifest does not match the full ledger')
    return True
