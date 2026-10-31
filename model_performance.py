"""Public, read-only display of published model evaluation evidence."""
import datetime as dt
import pandas as pd
import requests
import streamlit as st

REPORT_URL = 'https://raw.githubusercontent.com/Bruce-zda/matchlab-ai/main/artifacts/model_comparison.json'

@st.cache_data(ttl=120, show_spinner=False)
def load_public_comparison():
    response = requests.get(REPORT_URL, timeout=12)
    if response.status_code == 404:
        raise FileNotFoundError('Report has not been published yet')
    response.raise_for_status()
    report = response.json()
    if not isinstance(report, dict) or not report.get('models'):
        raise ValueError('Comparison report is incomplete')
    return report

def show_model_performance():
    st.subheader('Model Performance')
    st.caption('Independent of bookmaker odds · Historical evidence, not guaranteed outcomes')
    if st.button('Refresh model results', key='refresh_model_results'):
        load_public_comparison.clear()
    try:
        report = load_public_comparison()
    except FileNotFoundError:
        st.info('The evaluation report has not been published yet. Try refreshing in a moment.')
        return
    except (requests.RequestException, ValueError, TypeError) as exc:
        st.warning('The published evaluation report is temporarily unavailable.')
        return
    if report is None:
        st.info('The first verified comparison report has not been published yet. No winner is declared.')
        return
    if report.get('evaluation') != 'exploratory_frozen_chronological_folds_not_untouched':
        st.warning('Unknown evaluation methodology. Results are not endorsed.')
        return
    models = pd.DataFrame(report['models'])
    required = {'model','predictions','mean_brier','mean_log_loss'}
    if not required.issubset(models.columns):
        st.warning('Published comparison data is missing required metrics.')
        return
    st.info('EXPLORATORY EVIDENCE · Not an untouched final validation. No model has been promoted.')
    st.metric('Identical held-out fixtures', int(report.get('paired_fixtures',0)))
    st.metric('Leagues assessed', int(report.get('leagues',0)))
    view = models.rename(columns={'model':'Model','predictions':'Predictions',
                                  'mean_brier':'Brier score ↓','mean_log_loss':'Log loss ↓'})
    st.dataframe(view.style.format({'Brier score ↓':'{:.4f}','Log loss ↓':'{:.4f}'}),
                 hide_index=True, use_container_width=True)
    if len(models)==2 and models['predictions'].nunique()==1:
        brier_winner = models.loc[models.mean_brier.idxmin(),'model']
        log_winner = models.loc[models.mean_log_loss.idxmin(),'model']
        if brier_winner == log_winner:
            st.caption(f'{brier_winner} has the lower exploratory scores on both metrics; this is not a final validated winner.')
        else:
            st.caption('The metrics disagree on which model performed better. No clear exploratory leader.')
    for caveat in report.get('caveats',[]):
        st.caption('• '+str(caveat))
    st.caption('Reports are published by the GitHub evaluation workflow. Scores are not calculated from bookmaker odds.')
