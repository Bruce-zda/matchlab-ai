"""Regression checks for standalone production forecasting without Streamlit."""
import ast
import pathlib
import unittest
import numpy as np
from football_models import forecast, fit_dc, fetch_season

ROOT=pathlib.Path(__file__).resolve().parents[1]

class StandaloneModelTests(unittest.TestCase):
    def test_standalone_module_has_no_streamlit_import(self):
        tree=ast.parse((ROOT/'football_models.py').read_text())
        imports=[node for node in ast.walk(tree) if isinstance(node,(ast.Import,ast.ImportFrom))]
        for node in imports:
            names=[a.name for a in node.names] if isinstance(node,ast.Import) else [node.module or '']
            self.assertNotIn('streamlit',names)

    def test_collector_loads_standalone_functions(self):
        from scripts.collect_forward import models_from_app
        models=models_from_app()
        self.assertIs(models['forecast'],forecast)
        self.assertIs(models['fit_dc'],fit_dc)
        self.assertIs(models['fetch_season'],fetch_season)

    def test_numpy_json_serialization(self):
        import json
        from scripts.collect_forward import json_native
        payload={'goals':np.int64(3),'probability':np.float64(0.6),'grid':np.array([1,2])}
        self.assertEqual(json.loads(json.dumps(payload,default=json_native)),{'goals':3,'probability':0.6,'grid':[1,2]})

    def test_optimizer_converges_on_reproducible_history(self):
        import pandas as pd
        rng=np.random.default_rng(2026)
        teams=['Alpha','Bravo','Charlie','Delta','Echo','Foxtrot']
        rows=[]
        for i in range(180):
            home=teams[i%6]
            away=teams[(i+1+(i//6)%5)%6]
            rows.append({'Date':pd.Timestamp('2025-01-01')+pd.Timedelta(days=i),
                         'HomeTeam':home,'AwayTeam':away,
                         'FTHG':int(rng.poisson(1.5)),'FTAG':int(rng.poisson(1.1))})
        model=fit_dc(pd.DataFrame(rows))
        self.assertEqual(set(model[0]),set(teams))
        self.assertTrue(all(np.isfinite(v) for v in model[3:]))

    def test_score_grid_is_normalized(self):
        model=(['Home','Away'],{'Home':0.,'Away':0.},{'Home':0.,'Away':0.},0.2,0.0,0.0)
        lam,mu,grid=forecast(model,'Home','Away')
        self.assertTrue(np.isfinite(grid).all())
        self.assertAlmostEqual(float(grid.sum()),1.0,places=8)
        self.assertTrue((grid>=0).all())
        self.assertGreater(lam,0)
        self.assertGreater(mu,0)

if __name__=='__main__':
    unittest.main()
