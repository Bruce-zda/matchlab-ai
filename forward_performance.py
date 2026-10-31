"""Read-only dashboard of independently published forward-test evidence."""
import datetime as dt
import pandas as pd
import requests
import streamlit as st
from forward_integrity import verify

BASE='https://raw.githubusercontent.com/Bruce-zda/matchlab-ai/main/artifacts/'

@st.cache_data(ttl=120,show_spinner=False)
def load_forward_evidence():
    payload={}
    for name in ('forward_ledger.json','forward_settlements.json','forward_results_report.json'):
        response=requests.get(BASE+name,timeout=12)
        response.raise_for_status()
        payload[name]=response.json()
    for name in ('forward_coverage.json','forward_integrity.json'):
        response=requests.get(BASE+name,timeout=12)
        if response.status_code==404:
            continue
        response.raise_for_status()
        payload[name]=response.json()
    return payload

def show_forward_performance():
    st.subheader('Forward Performance · Live Pilot')
    st.caption('Pre-kickoff archived forecasts · Verified final results only · No bookmaker odds')
    if st.button('Refresh forward evidence',key='refresh_forward_evidence'):
        load_forward_evidence.clear()
    try:
        data=load_forward_evidence()
    except (requests.RequestException,ValueError,TypeError):
        st.warning('Forward evidence is temporarily unavailable; no performance claims can be made.')
        return
    ledger=data['forward_ledger.json']
    settled=data['forward_settlements.json']
    report=data['forward_results_report.json']
    if not isinstance(ledger,list) or not isinstance(settled,list) or not isinstance(report,dict):
        st.warning('Unexpected forward evidence format.')
        return
    proof=data.get('forward_integrity.json')
    if proof is not None:
        try:
            verify(ledger,proof)
            st.caption('Full-record SHA-256 manifest: verified against published ledger.')
        except (ValueError,TypeError):
            st.error('FORECAST INTEGRITY CHECK FAILED. Published manifest and ledger disagree.')
            return
    coverage=data.get('forward_coverage.json')
    if isinstance(coverage,dict) and coverage.get('fixture_count'):
        count=coverage['fixture_count']
        covered=coverage.get('covered',0)
        pct=covered/count*100
        st.metric('Latest collection coverage',f'{pct:.1f}%',f'{covered}/{count} fixtures',delta_color='off')
        if pct<90:
            st.warning('Coverage below 90% target. Skipped fixtures require review; no guesses are substituted.')
        else:
            st.success('Latest collection reached the 90% fixture coverage target.')
        skipped=[x for x in coverage.get('details',[]) if x.get('status')=='skipped']
        if skipped:
            with st.expander(f'Skipped fixtures ({len(skipped)})'):
                st.dataframe(pd.DataFrame(skipped),hide_index=True,use_container_width=True)
    fixture_ids={r.get('provider_match_id') for r in ledger}
    settled_ids={r.get('provider_match_id') for r in settled}
    a,b,c=st.columns(3)
    a.metric('Forecasts archived',len(ledger))
    b.metric('Fixtures monitored',len(fixture_ids))
    c.metric('Fixtures settled',len(settled_ids))
    if ledger:
        times=pd.to_datetime([r.get('captured_at_utc') for r in ledger],utc=True,errors='coerce')
        kicks=pd.to_datetime([r.get('kickoff_utc') for r in ledger],utc=True,errors='coerce')
        pre=int((times<kicks).sum())
        st.caption(f'Pre-kickoff timestamps: {pre}/{len(ledger)} · Model versions and provider IDs retained.')
    if not settled:
        st.info('No verified completed matches have been settled yet. Model performance is not available.')
    else:
        scores=report.get('models',[])
        if scores:
            table=pd.DataFrame(scores).rename(columns={'model':'Model','n':'Settled forecasts',
                'mean_brier':'Brier ↓','mean_log_loss':'Log loss ↓'})
            st.dataframe(table.style.format({'Brier ↓':'{:.4f}','Log loss ↓':'{:.4f}'}),
                         hide_index=True,use_container_width=True)
        st.warning('Pilot sample only. No model promotion or claims of superiority from these results.')
    paired=report.get('paired_comparison',{})
    if isinstance(paired,dict):
        st.markdown('**Head-to-head · Dixon–Coles vs 50/50 Hybrid**')
        n=paired.get('paired_fixtures',0)
        st.caption(f'Identical settled fixtures: {n} · Negative deltas favor the hybrid.')
        if n:
            st.metric('Paired Brier difference',f"{paired['mean_brier_delta']:+.5f}")
            st.metric('Paired log-loss difference',f"{paired['mean_log_loss_delta']:+.5f}")
            ci=paired.get('bootstrap_95pct_ci')
            if ci:
                st.caption(f"League-month bootstrap 95% intervals: Brier {ci['brier_delta']} · Log loss {ci['log_loss_delta']}")
        else:
            st.info('Awaiting verified paired results; no head-to-head performance claims yet.')
        st.caption('Pilot comparison only; model promotion remains disabled.')
    audit=report.get('audit',{})
    st.caption(f"Awaiting verified results: {audit.get('awaiting_verified_result','?')} forecasts · "
               f"Provider conflicts: {audit.get('conflicting_provider_results','?')}")
    if ledger:
        st.markdown('**Latest archived fixtures**')
        unique={}
        for r in ledger:
            key=r.get('provider_match_id')
            if key not in unique:
                unique[key]={'Kickoff (UTC)':r.get('kickoff_utc'),
                             'League':r.get('league'),'Fixture':f"{r.get('home')} vs {r.get('away')}",
                             'Status':'Settled' if key in settled_ids else 'Awaiting result'}
        view=pd.DataFrame(list(unique.values())).sort_values('Kickoff (UTC)').head(20)
        st.dataframe(view,hide_index=True,use_container_width=True)
    st.caption('Scores are updated by the scheduled GitHub settlement workflow. Forward evidence is independent of historical backtests.')
