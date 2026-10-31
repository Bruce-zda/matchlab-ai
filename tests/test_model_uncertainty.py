import unittest
import pandas as pd
from model_uncertainty import paired_interval

class PairedIntervalTests(unittest.TestCase):
    def test_repeated_fixture_across_folds_is_distinct(self):
        rows=[]
        for fold in (1,2):
            for month in range(1,5):
                for model,score in (('Dixon-Coles',0.21),('DC + Bayesian (50/50)',0.20)):
                    rows.append({'league':'League','fold':fold,'date':f'2025-{month:02d}-01',
                                 'home':'A','away':'B','actual':0,'model':model,'brier':score})
        result=paired_interval(pd.DataFrame(rows),repetitions=100)
        self.assertEqual(result['paired_fixtures'],8)
        self.assertAlmostEqual(result['difference'],-0.01)

    def test_duplicate_within_fold_rejected(self):
        rows=[]
        for month in range(1,5):
            for model in ('Dixon-Coles','DC + Bayesian (50/50)'):
                rows.append({'league':'League','fold':1,'date':f'2025-{month:02d}-01',
                             'home':'A','away':'B','actual':0,'model':model,'brier':0.2})
        rows.append(dict(rows[0]))
        with self.assertRaises(ValueError):
            paired_interval(pd.DataFrame(rows),repetitions=100)

if __name__=='__main__':
    unittest.main()
