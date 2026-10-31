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


if __name__ == "__main__":
    unittest.main()
