"""MatchLab Discover: archived, timestamped football forecasts."""
import datetime as dt
import html
from collections import defaultdict
import pandas as pd
import streamlit as st
from forward_performance import load_forward_evidence

MODEL_NAMES = ('Dixon-Coles', 'Bayesian Goals', 'Elo', 'DC + Bayesian (50/50)')


def _safe(value):
    return html.escape(str(value), quote=True)


def _bar(home, draw, away):
    widths = [max(0, min(100, 100 * float(v))) for v in (home, draw, away)]
    return (f'<div class="ml-prob-track" aria-label="Home {widths[0]:.1f} percent, '
            f'draw {widths[1]:.1f} percent, away {widths[2]:.1f} percent">'
            f'<span style="width:{widths[0]:.3f}%;background:#4fd1a5"></span>'
            f'<span style="width:{widths[1]:.3f}%;background:#e9b968"></span>'
            f'<span style="width:{widths[2]:.3f}%;background:#7898ff"></span></div>')


def show_discover():
    st.markdown("""<style>
    .ml-hero{padding:30px 30px 25px;border-radius:22px;border:1px solid #344a5a;
    background:radial-gradient(ellipse at 90% 5%,#254e54 0%,transparent 45%),
    linear-gradient(120deg,#1a2a39,#111b26);margin:8px 0 25px}
    .ml-kicker{font-size:.7rem;letter-spacing:.18em;color:#80e2c4;font-weight:800}
    .ml-headline{font-size:clamp(1.8rem,5vw,3.2rem);font-weight:850;letter-spacing:-.065em;
    line-height:1.12;margin:12px 0}
    .ml-sub{color:#afc1ce;font-size:.94rem;max-width:660px;line-height:1.6}
    .ml-fixture{border:1px solid #30404e;background:linear-gradient(115deg,#192531,#131d28);
    padding:20px 22px;border-radius:16px;margin:12px 0}
    .ml-meta{font-size:.72rem;color:#a9bdca;letter-spacing:.07em}
    .ml-teams{font-size:clamp(1.18rem,3vw,1.62rem);font-weight:790;letter-spacing:-.035em;
    margin:12px 0 16px}
    .ml-prob-track{display:flex;height:11px;border-radius:99px;overflow:hidden;
    background:#2c3944;gap:2px;margin:12px 0 9px}
    .ml-prob-track span{display:block;height:100%}
    .ml-legend{display:flex;justify-content:space-between;gap:6px;font-size:.78rem;color:#cad7df}
    .ml-legend strong{font-size:.94rem;color:#f4f8fa}
    .ml-foot{font-size:.73rem;color:#8ca0ae;margin-top:13px;line-height:1.5}
    .ml-section-label{font-size:.72rem;letter-spacing:.13em;text-transform:uppercase;color:#9db2c4;font-weight:750;margin:18px 0 7px}
    .ml-health{font-size:.78rem;color:#8fe0c5;margin:8px 0 16px}
    .ml-pill{display:inline-block;padding:4px 9px;border:1px solid #42665d;border-radius:30px;
    color:#8fe0c5;background:#19352f;font-size:.68rem;font-weight:750}
    @media(max-width:650px){.ml-hero{padding:22px 18px}.ml-fixture{padding:17px 15px}
    .ml-legend{font-size:.68rem}.ml-legend strong{font-size:.82rem}}
    </style>""", unsafe_allow_html=True)
    st.markdown("""<div class="ml-hero"><div class="ml-kicker">MATCHLAB / DISCOVER</div>
    <div class="ml-headline">Football predictions.<br>Evidence first.</div>
    <div class="ml-sub">Explore real archived forecasts, compare independent models,
    and follow what happens after the final whistle. No fabricated certainty.</div></div>""",
    unsafe_allow_html=True)
    try:
        data = load_forward_evidence()
        ledger = data.get('forward_ledger.json', [])
        settled = data.get('forward_settlements.json', [])
    except (ValueError, TypeError, KeyError, Exception) as exc:
        st.warning('The published forecast feed is temporarily unavailable.')
        return
    if not isinstance(ledger, list) or not ledger:
        st.info('No archived forecasts available yet.')
        return
    from forward_integrity import verify
    manifest = data.get('forward_integrity.json')
    if manifest is None:
        st.warning('Forecast integrity manifest is unavailable; cards are withheld.')
        return
    try:
        verify(ledger, manifest)
    except (ValueError, TypeError):
        st.error('Published forecast integrity mismatch. Cards are withheld.')
        return
    fixtures = defaultdict(dict)
    metadata = {}
    for row in ledger:
        fid = row.get('provider_match_id')
        if fid is None:
            continue
        fixtures[fid][row.get('model')] = row
        metadata[fid] = row
    now = dt.datetime.now(dt.timezone.utc)
    settled_ids = {r.get('provider_match_id') for r in settled if isinstance(r, dict)}
    st.markdown('<div class="ml-health">● Archive integrity verified · Pre-match snapshots</div>', unsafe_allow_html=True)
    leagues = sorted({r.get('league', 'Unknown') for r in metadata.values()})
    col1, col2 = st.columns([1.2, 1])
    with col1:
        league = st.selectbox('Competition', ['All leagues'] + leagues, key='ml_discover_league')
    with col2:
        period = st.selectbox('Fixtures', ['Upcoming', 'All archived', 'Completed / past'],
                              key='ml_discover_period')
    candidates = []
    for fid, row in metadata.items():
        try:
            kickoff = dt.datetime.fromisoformat(row['kickoff_utc'].replace('Z', '+00:00'))
        except (ValueError, KeyError, TypeError):
            continue
        if league != 'All leagues' and row.get('league') != league:
            continue
        if period == 'Upcoming' and kickoff <= now:
            continue
        if period == 'Completed / past' and kickoff > now:
            continue
        candidates.append((kickoff, fid, row))
    candidates.sort(key=lambda x: x[0], reverse=(period == 'Completed / past'))
    st.caption(f'{len(candidates)} fixtures · Archived predictions only · UTC kickoff times')
    if not candidates:
        st.info('No fixtures match these filters. Try All archived.')
        return
    page_size = 12
    total_pages = (len(candidates) + page_size - 1) // page_size
    page = st.number_input('Results page', min_value=1, max_value=total_pages, value=1, step=1,
                           key='ml_discover_page') if total_pages > 1 else 1
    start = (page - 1) * page_size
    for kickoff, fid, row in candidates[start:start + page_size]:
        models = fixtures[fid]
        primary = models.get('Dixon-Coles')
        if not primary:
            continue
        h, d, a = (float(primary[k]) for k in ('p_home', 'p_draw', 'p_away'))
        status = ('Verified result archived' if fid in settled_ids else
                  'Awaiting verified result' if kickoff <= now else 'Scheduled')
        with st.container():
            st.markdown(
                f'<div class="ml-fixture"><div class="ml-meta">{_safe(row.get("league",""))} '
                f'&nbsp;·&nbsp; {_safe(kickoff.strftime("%d %b %Y · %H:%M UTC"))}'
                f'&nbsp;·&nbsp; {_safe(status)}</div>'
                f'<div class="ml-teams">{_safe(row.get("home","Home"))} '
                f'<span style="color:#748999;font-weight:500">vs</span> '
                f'{_safe(row.get("away","Away"))}</div>'
                f'<span class="ml-pill">DIXON–COLES · PRIMARY</span>'
                + _bar(h, d, a)
                + f'<div class="ml-legend"><span>Home <strong>{h:.1%}</strong></span>'
                f'<span>Draw <strong>{d:.1%}</strong></span>'
                f'<span>Away <strong>{a:.1%}</strong></span></div>'
                f'<div class="ml-foot">Recorded {_safe(primary.get("captured_at_utc","unknown"))}'
                ' · Forecast, not a guaranteed outcome.</div></div>',
                unsafe_allow_html=True)
            with st.expander(f'Open Match Centre · {row.get("home","")} vs {row.get("away","")}', expanded=False):
                st.markdown('### Match Centre')
                st.caption('01 / Probability breakdown · 02 / Prediction markets · 03 / Analysis · 04 / Research outlook')
                entries = []
                for name in MODEL_NAMES:
                    item = models.get(name)
                    if item:
                        entries.append({'Model': name, 'Home': float(item['p_home']),
                                        'Draw': float(item['p_draw']),
                                        'Away': float(item['p_away'])})
                if entries:
                    frame = pd.DataFrame(entries)
                    st.dataframe(frame.style.format({'Home':'{:.1%}','Draw':'{:.1%}',
                                                      'Away':'{:.1%}'}),
                                 hide_index=True, use_container_width=True)
                    if len(entries) > 1:
                        spreads = [max(e[k] for e in entries) - min(e[k] for e in entries)
                                   for k in ('Home','Draw','Away')]
                        st.caption(f'Maximum model disagreement: {max(spreads):.1%} '
                                   'percentage points across the three outcomes.')
                from match_intelligence_view import (
                    archived_goal_market_rows, archived_research_screen, LABELS)
                hybrid = models.get('DC + Bayesian (50/50)')
                if hybrid:
                    try:
                        market_rows = archived_goal_market_rows(hybrid)
                        frozen = archived_research_screen(hybrid)
                    except ValueError:
                        st.error('Archived goal-market integrity check failed; market details withheld.')
                        market_rows, frozen = [], None
                    if market_rows:
                        st.markdown('#### 02 / Prediction markets')
                        st.caption('Frozen pre-match hybrid probabilities · research-stage estimates')
                        groups = {
                            'Totals': [r for r in market_rows if r['Market'].startswith('Total goals')],
                            'Both teams to score': [r for r in market_rows if r['Market'].startswith('Both teams')],
                            'Home team goals': [r for r in market_rows if r['Market'].startswith('Home goals')],
                            'Away team goals': [r for r in market_rows if r['Market'].startswith('Away goals')],
                        }
                        tabs = st.tabs(list(groups))
                        for tab, group in zip(tabs, groups.values()):
                            with tab:
                                st.dataframe(pd.DataFrame(group).style.format({'Probability': '{:.1%}'}),
                                             hide_index=True, use_container_width=True)
                        st.markdown('#### 04 / MatchLab research outlook')
                        if isinstance(frozen, dict):
                            candidate = frozen.get('candidate')
                            if frozen.get('status') == 'RESEARCH_SCREEN_ONLY' and isinstance(candidate, dict):
                                label = LABELS.get(candidate.get('market'), candidate.get('market'))
                                st.info(f"Research screen: {label} · {candidate['probability']:.1%} model probability. Not a verified expert pick.")
                            else:
                                st.caption('Research screen abstained: no market met its evidence thresholds.')
                        else:
                            st.caption('This older forecast has no frozen selection screen; no retrospective selection is assigned.')
                # Expert-style interpretation grounded exclusively in archived probabilities.
                winner_index = max(range(3), key=lambda i: (h, d, a)[i])
                labels = [f'{row.get("home", "Home")} win', 'Draw',
                          f'{row.get("away", "Away")} win']
                probs = (h, d, a)
                ordered = sorted(probs, reverse=True)
                margin = ordered[0] - ordered[1]
                confidence = ('close contest' if margin < 0.08 else
                              'moderate separation' if margin < 0.18 else
                              'clear probability leader')
                st.markdown('#### 03 / Model-based analysis')
                st.markdown(f'**Most likely result: {labels[winner_index]} — {probs[winner_index]:.1%}**')
                st.caption('Highest-probability 1X2 outcome from the primary Dixon–Coles model; '
                           'not a guaranteed result or a predicted exact score.')
                st.write(f'The model assigns {h:.1%} to a home win, {d:.1%} to a draw '
                         f'and {a:.1%} to an away win. This is a {confidence}: '
                         f'the leading outcome is {margin:.1%} percentage points '
                         'ahead of the next most likely outcome.')
                if len(entries) > 1:
                    leaders = []
                    for item in entries:
                        vals = (item['Home'], item['Draw'], item['Away'])
                        leaders.append(max(range(3), key=lambda i: vals[i]))
                    agreement = sum(i == winner_index for i in leaders)
                    st.write(f'**Model consensus:** {agreement} of {len(entries)} archived models '
                             'select the same most likely 1X2 outcome.')
                    if agreement < len(entries):
                        st.info('Models disagree on the leading outcome. Treat this '
                                'forecast as less decisive.')
                st.caption('Analysis uses archived model probabilities only. No injury, lineup, '
                           'form or news claims are inferred without verified inputs.')
                st.caption('Model probabilities are descriptive, not betting recommendations. '
                           'The hybrid is experimental and has not been promoted.')
    if total_pages > 1:
        st.caption(f'Page {page} of {total_pages} · {len(candidates)} archived fixtures')
