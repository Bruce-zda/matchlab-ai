"""Pure presentation helpers for archived goal-market forecasts.

No prediction is generated or retroactively selected by this module.
"""
import math

LABELS = {"btts_yes": "Both teams to score · Yes",
          "btts_no": "Both teams to score · No"}
for threshold in ("1_5", "2_5", "3_5"):
    for direction in ("over", "under"):
        LABELS[f"{direction}_{threshold}"] = f"Total goals {direction} {threshold.replace('_', '.')}"
for side in ("home", "away"):
    for threshold in ("0_5", "1_5", "2_5"):
        for direction in ("over", "under"):
            LABELS[f"{side}_{direction}_{threshold}"] = (
                f"{side.title()} goals {direction} {threshold.replace('_', '.')}")


def archived_goal_market_rows(hybrid):
    """Display only known, finite, bounded pre-match goal probabilities."""
    if not isinstance(hybrid, dict):
        return []
    data = hybrid.get("goal_markets")
    markets = data.get("markets", {}) if isinstance(data, dict) else {}
    if not isinstance(markets, dict):
        return []
    rows = []
    for key, value in markets.items():
        if key not in LABELS:
            continue
        if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= 1:
            raise ValueError("Invalid archived goal-market probability")
        rows.append({"Market": LABELS[key], "Probability": float(value)})
    return sorted(rows, key=lambda item: (-item["Probability"], item["Market"]))


def archived_research_screen(hybrid):
    """Return the archived decision, never a reconstructed retrospective pick."""
    if not isinstance(hybrid, dict):
        return None
    frozen = hybrid.get("frozen_screen")
    if frozen is None:
        return None
    from intelligence_selection import screen_outlook
    markets = hybrid.get("screen_markets")
    if not isinstance(markets, list) or frozen != screen_outlook(markets):
        raise ValueError("Archived frozen screen integrity mismatch")
    return frozen
