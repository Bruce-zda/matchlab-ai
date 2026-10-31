"""Optional market-price comparison. Never feeds the forecasting model."""
import datetime as dt
import math

SPORT_KEYS = {
    'Premier League': 'soccer_epl',
    'La Liga': 'soccer_spain_la_liga',
    'Serie A': 'soccer_italy_serie_a',
    'Bundesliga': 'soccer_germany_bundesliga',
    'Ligue 1': 'soccer_france_ligue_one',
}


def implied_probability(decimal_odds):
    try:
        value = float(decimal_odds)
    except (TypeError, ValueError, OverflowError):
        return None
    if not math.isfinite(value) or value <= 1:
        return None
    return 1 / value


def compare_h2h(events, home, away, fixture_date, normalize):
    """Require exact normalized teams and kickoff date; never fuzzy-match odds."""
    matches = []
    for event in events:
        if normalize(event.get('home_team', '')) != normalize(home):
            continue
        if normalize(event.get('away_team', '')) != normalize(away):
            continue
        try:
            kickoff = dt.datetime.fromisoformat(event['commence_time'].replace('Z', '+00:00'))
        except (ValueError, TypeError, KeyError, AttributeError):
            continue
        if fixture_date is not None and abs((kickoff.date() - fixture_date).days) > 1:
            continue
        matches.append(event)
    if len(matches) != 1:
        return []
    rows = []
    for book in matches[0].get('bookmakers', []):
        for market in book.get('markets', []):
            if market.get('key') != 'h2h':
                continue
            prices = {}
            for outcome in market.get('outcomes', []):
                name = outcome.get('name', '')
                label = ('Home' if normalize(name) == normalize(home) else
                         'Away' if normalize(name) == normalize(away) else
                         'Draw' if name.lower() == 'draw' else None)
                if label is not None:
                    prices[label] = implied_probability(outcome.get('price'))
            if set(prices) != {'Home', 'Draw', 'Away'} or any(p is None for p in prices.values()):
                continue
            margin = sum(prices.values()) - 1
            if margin < -0.01 or margin > 0.4:
                continue
            for label in ('Home', 'Draw', 'Away'):
                rows.append({'Bookmaker': book.get('title', 'Unknown'),
                             'Outcome': label,
                             'Decimal odds': round(1 / prices[label], 3),
                             'Implied %': round(100 * prices[label], 1),
                             'No-vig %': round(100 * prices[label] / sum(prices.values()), 1),
                             'Bookmaker margin %': round(100 * margin, 1),
                             'Updated': market.get('last_update', book.get('last_update', 'Unknown'))})
    return rows
