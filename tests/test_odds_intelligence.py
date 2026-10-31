import datetime as dt
import unittest
from odds_intelligence import implied_probability, compare_h2h


def norm(s):
    return str(s).lower().replace(' ', '')


class OddsTests(unittest.TestCase):
    def test_implied_probability(self):
        self.assertAlmostEqual(implied_probability(2), .5)
        for value in [None, 0, 1, -3, 'bad', float('nan')]:
            self.assertIsNone(implied_probability(value))

    def test_exact_match_and_margin(self):
        event = {
            'home_team': 'Chelsea', 'away_team': 'Arsenal',
            'commence_time': '2026-11-01T16:00:00Z',
            'bookmakers': [{'title': 'Demo', 'markets': [{'key': 'h2h',
                'outcomes': [{'name': 'Chelsea', 'price': 2.0},
                             {'name': 'Draw', 'price': 3.5},
                             {'name': 'Arsenal', 'price': 4.0}]}]}]
        }
        rows = compare_h2h([event], 'Chelsea', 'Arsenal', dt.date(2026, 11, 1), norm)
        self.assertEqual(len(rows), 3)
        self.assertAlmostEqual(sum(row['No-vig %'] for row in rows), 100, places=1)
        self.assertEqual(compare_h2h([event, event], 'Chelsea', 'Arsenal', None, norm), [])
        self.assertEqual(compare_h2h([event], 'Chelsea', 'Liverpool', None, norm), [])


if __name__ == '__main__':
    unittest.main()
