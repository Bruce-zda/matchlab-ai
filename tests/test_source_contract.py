"""Basic source-contract checks for MatchLab's Streamlit application."""
import ast
import pathlib
import unittest

APP = pathlib.Path(__file__).resolve().parents[1] / "app.py"


class SourceContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = APP.read_text(encoding="utf-8")
        cls.tree = ast.parse(cls.source, filename=str(APP))

    def test_python_compiles(self):
        compile(self.source, str(APP), "exec")

    def test_streamlit_widget_keys_are_unique_in_source(self):
        """Catch literal duplicate widget keys (the cause of the previous outage)."""
        seen = {}
        widget_names = {
            "radio", "select_slider", "slider", "selectbox", "multiselect",
            "text_input", "number_input", "checkbox", "toggle", "date_input",
            "time_input", "button", "download_button", "file_uploader",
        }
        for node in ast.walk(self.tree):
            if not isinstance(node, ast.Call):
                continue
            if not isinstance(node.func, ast.Attribute) or node.func.attr not in widget_names:
                continue
            for keyword in node.keywords:
                if keyword.arg != "key":
                    continue
                if isinstance(keyword.value, ast.Constant) and isinstance(keyword.value.value, str):
                    key = keyword.value.value
                    self.assertNotIn(key, seen, f"Duplicate literal widget key {key!r} at lines {seen.get(key)} and {node.lineno}")
                    seen[key] = node.lineno

    def test_handicap_controls_have_distinct_keys(self):
        """Keep the controls that previously caused StreamlitDuplicateElementKey."""
        self.assertIn("ah_side_{home}_{away}", self.source)
        self.assertIn("ah_line_{home}_{away}", self.source)

    def test_core_features_present(self):
        for feature in ("def fit_dc(", "def forecast(", "def rolling_league_evaluation(",
                        "Double chance", "Asian handicap"):
            with self.subTest(feature=feature):
                self.assertIn(feature, self.source)

    def test_calibration_is_evaluation_only(self):
        """Calibration must not silently alter the live match forecast."""
        self.assertIn("from calibration import chronological_calibration_report", self.source)
        self.assertIn("report=chronological_calibration_report(binary_p,binary_y)", self.source)
        forecast = next(n for n in self.tree.body if isinstance(n, ast.FunctionDef) and n.name == "forecast")
        live_source = ast.get_source_segment(self.source, forecast)
        self.assertNotIn("calibrat", live_source.lower())
        self.assertIn("calibration raw Brier", self.source)
        self.assertIn("calibration adjusted Brier", self.source)

    def test_match_card_uses_evidence_aware_ranking(self):
        self.assertIn("rank_model_outlooks(dc_probabilities,evidence_status)", self.source)
        self.assertIn("No clear market advantage", self.source)
        self.assertIn("Research-stage assessment", self.source)
        self.assertNotIn("Expert-approved pick", self.source)

    def test_history_window_and_validation_contract(self):
        history = next(n for n in self.tree.body if isinstance(n, ast.FunctionDef) and n.name == "get_league")
        source = ast.get_source_segment(self.source, history)
        self.assertIn("range(year-7,year+1)", source)
        self.assertIn("drop_duplicates", source)
        self.assertIn("empty archive", source)
        self.assertIn("valid_score_pair(row.FTHG,row.FTAG)", self.source)
        self.assertIn("valid_team_pair(row.HomeTeam,row.AwayTeam)", self.source)

    def test_standalone_report_imports_project_root(self):
        report = APP.parent / "scripts" / "calibration_report.py"
        source = report.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(report))
        compile(source, str(report), "exec")
        self.assertIn("sys.path.insert(0, str(ROOT))", source)
        self.assertLess(source.index("sys.path.insert(0, str(ROOT))"),
                        source.index("from calibration import"))


if __name__ == "__main__":
    unittest.main()
