import unittest
import numpy as np
import pandas as pd
from bayesian_goals import BayesianGoals

class BayesianGoalsTests(unittest.TestCase):
    def setUp(self):
        self.matches = pd.DataFrame([
            {'HomeTeam':'Alpha','AwayTeam':'Beta','FTHG':2,'FTAG':1},
            {'HomeTeam':'Beta','AwayTeam':'Alpha','FTHG':0,'FTAG':1},
            {'HomeTeam':'Alpha','AwayTeam':'Gamma','FTHG':3,'FTAG':0},
            {'HomeTeam':'Gamma','AwayTeam':'Beta','FTHG':1,'FTAG':1},
        ] * 8)

    def test_probabilities_valid(self):
        model=BayesianGoals().fit(self.matches)
        probabilities=model.predict('Alpha','Beta')
        self.assertEqual(len(probabilities),3)
        self.assertTrue(np.isfinite(probabilities).all())
        self.assertTrue((probabilities>=0).all())
        self.assertAlmostEqual(sum(probabilities),1.0,places=10)

    def test_no_unseen_team_predictions(self):
        model=BayesianGoals().fit(self.matches)
        with self.assertRaises(ValueError):
            model.predict('Unknown','Beta')

    def test_small_training_rejected(self):
        with self.assertRaises(ValueError):
            BayesianGoals().fit(self.matches.head(3))

    def test_training_changes_predictions(self):
        model=BayesianGoals().fit(self.matches)
        baseline=model.predict('Alpha','Beta')
        changed=self.matches.copy()
        changed.loc[changed.HomeTeam=='Alpha','FTHG']=5
        updated=BayesianGoals().fit(changed).predict('Alpha','Beta')
        self.assertFalse(np.allclose(baseline,updated))

if __name__=='__main__':
    unittest.main()
