"""Independent, pre-match Elo 1X2 baseline. No bookmaker inputs.

Draw propensity is estimated from training matches only; all ratings are
updated strictly after each completed result. Evaluation must use future data.
"""
import math

def _probabilities(home_rating, away_rating, draw_rate, home_advantage=65.0):
    expected_home = 1.0 / (1.0 + 10.0 ** ((away_rating - home_rating - home_advantage) / 400.0))
    # Draw adjustment is a fixed training-only parameter, not future information.
    draw = min(0.45, max(0.10, draw_rate)) * (1.0 - abs(2 * expected_home - 1) ** 1.5)
    home = (1.0 - draw) * expected_home
    away = (1.0 - draw) * (1.0 - expected_home)
    return home, draw, away

class EloBaseline:
    def __init__(self, k=24.0, home_advantage=65.0):
        self.k = float(k)
        self.home_advantage = float(home_advantage)
        self.ratings = {}
        self.draw_rate = 0.26
        self.matches = 0

    def predict(self, home, away):
        return _probabilities(self.ratings.get(home, 1500.0),
                              self.ratings.get(away, 1500.0),
                              self.draw_rate, self.home_advantage)

    def observe(self, home, away, home_goals, away_goals):
        from data_quality import valid_score_pair, valid_team_pair
        if not valid_team_pair(home, away) or not valid_score_pair(home_goals, away_goals):
            raise ValueError("Invalid completed match")
        hr = self.ratings.get(home, 1500.0)
        ar = self.ratings.get(away, 1500.0)
        expectation = 1 / (1 + 10 ** ((ar - hr - self.home_advantage) / 400))
        outcome = 1.0 if home_goals > away_goals else 0.0 if home_goals < away_goals else 0.5
        change = self.k * (outcome - expectation)
        self.ratings[home] = hr + change
        self.ratings[away] = ar - change
        # Expanding historical draw estimate, used only on subsequent matches.
        self.draw_rate = ((self.draw_rate * max(self.matches, 1)) +
                          (1.0 if home_goals == away_goals else 0.0)) / (max(self.matches, 1) + 1)
        self.matches += 1

def evaluate_elo(matches, warmup=100):
    """Chronological match records: (home, away, home_goals, away_goals)."""
    model = EloBaseline()
    predictions = []
    for home, away, hg, ag in matches:
        probabilities = model.predict(home, away)
        if model.matches >= warmup:
            outcome = 0 if hg > ag else 1 if hg == ag else 2
            predictions.append({'probabilities': probabilities, 'outcome': outcome,
                                'brier': sum((p - (i == outcome)) ** 2 for i, p in enumerate(probabilities)) / 3,
                                'log_loss': -math.log(max(probabilities[outcome], 1e-12))})
        model.observe(home, away, hg, ag)
    return predictions
