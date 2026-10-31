"""Input checks for external match feeds.

Fixtures are unverified community data; validation prevents malformed rows
from silently entering model training or the upcoming-match selector.
"""
import math


def valid_score_pair(home, away):
    try:
        h, a = float(home), float(away)
    except (TypeError, ValueError, OverflowError):
        return False
    return (math.isfinite(h) and math.isfinite(a) and h >= 0 and a >= 0
            and h.is_integer() and a.is_integer() and h <= 40 and a <= 40)


def valid_team_pair(home, away):
    return (isinstance(home, str) and isinstance(away, str)
            and bool(home.strip()) and bool(away.strip())
            and home.strip().casefold() != away.strip().casefold()
            and home.strip().casefold() not in {"nan", "none", "unknown"}
            and away.strip().casefold() not in {"nan", "none", "unknown"})
