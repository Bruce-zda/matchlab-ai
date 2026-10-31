import unittest
from data_quality import valid_score_pair, valid_team_pair


class DataQualityTests(unittest.TestCase):
    def test_valid_scores(self):
        self.assertTrue(valid_score_pair(2, 1))
        self.assertTrue(valid_score_pair("0", "0"))

    def test_invalid_scores(self):
        for home, away in [(-1, 2), (1.5, 0), (float("nan"), 0),
                           (float("inf"), 0), (41, 0), (None, 0),
                           ("x", 0)]:
            with self.subTest(home=home, away=away):
                self.assertFalse(valid_score_pair(home, away))

    def test_team_names(self):
        self.assertTrue(valid_team_pair("Chelsea", "Man Utd"))
        for home, away in [("Chelsea", "chelsea"), ("", "Liverpool"),
                           ("Unknown", "Arsenal"), (None, "Arsenal"),
                           ("NaN", "Spurs")]:
            with self.subTest(home=home, away=away):
                self.assertFalse(valid_team_pair(home, away))


if __name__ == "__main__":
    unittest.main()
