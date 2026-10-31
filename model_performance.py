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
    if len(models)>=2 and models['predictions'].nunique()==1:
        brier_winner = models.loc[models.mean_brier.idxmin(),'model']
        log_winner = models.loc[models.mean_log_loss.idxmin(),'model']
        if brier_winner == log_winner:
            st.caption(f'{brier_winner} has the lowest exploratory scores on both metrics; this is not a final validated winner.')
        else:
            st.caption('The metrics disagree on which model performed better. No clear exploratory leader.')
    if report.get('hybrid_uncertainty'):
        st.markdown('**Hybrid advantage: uncertainty check**')
        st.caption('Paired monthly block bootstrap; intervals crossing zero mean the observed advantage is not clearly separated from sampling noise.')
        uncertainty=pd.DataFrame(report['hybrid_uncertainty'])
        st.dataframe(uncertainty[['metric','difference','ci95_lower','ci95_upper','paired_fixtures']].rename(columns={'metric':'Score','difference':'Hybrid minus DC','ci95_lower':'95% lower','ci95_upper':'95% upper','paired_fixtures':'Fixtures'}).style.format({'Hybrid minus DC':'{:+.5f}','95% lower':'{:+.5f}','95% upper':'{:+.5f}'}),hide_index=True,use_container_width=True)
        st.caption('Exploratory intervals only: historical data was previously examined. Not evidence of future betting performance.')
    if report.get('league_metrics'):
        st.markdown('**League-by-league comparison**')
        league_view = pd.DataFrame(report['league_metrics'])
        league_view = league_view.rename(columns={'league':'League','model':'Model',
            'predictions':'Matches','mean_brier':'Brier ↓','mean_log_loss':'Log loss ↓'})
        st.dataframe(league_view.style.format({'Brier ↓':'{:.4f}','Log loss ↓':'{:.4f}'}),
                     hide_index=True,use_container_width=True)
    if report.get('calibration_bins'):
        st.markdown('**Probability reliability**')
        st.caption('Predicted probability versus actual frequency in ten fixed bins. Sparse bins are noisy.')
        bins = pd.DataFrame(report['calibration_bins'])
        selected = st.selectbox('Reliability model',sorted(bins.model.unique()),key='reliability_model')
        outcome = st.selectbox('Outcome',('home','draw','away'),key='reliability_outcome')
        view_bins = bins[(bins.model==selected)&(bins.outcome==outcome)]
        st.dataframe(view_bins[['mean_probability','observed_frequency','count']].rename(
            columns={'mean_probability':'Predicted','observed_frequency':'Observed','count':'Matches'}
        ).style.format({'Predicted':'{:.1%}','Observed':'{:.1%}'}),hide_index=True,use_container_width=True)
    for caveat in report.get('caveats',[]):
        st.caption('• '+str(caveat))
    st.caption('Reports are published by the GitHub evaluation workflow. Scores are not calculated from bookmaker odds.')
