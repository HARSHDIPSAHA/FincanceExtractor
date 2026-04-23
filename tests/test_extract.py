import unittest

from ifrs9_benchmark.extract import _extract_core_metrics, _extract_model_structure, _extract_scenario_design
from ifrs9_benchmark.models import TableData
from ifrs9_benchmark.utils import parse_number, safe_ratio


class UtilsTests(unittest.TestCase):
    def test_parse_number_parentheses(self) -> None:
        self.assertEqual(parse_number("(207.4)"), -207.4)
        self.assertEqual(parse_number("1,550.7"), 1550.7)

    def test_safe_ratio(self) -> None:
        self.assertAlmostEqual(safe_ratio(207.4, 1477.8), 0.140341)


class ExtractTests(unittest.TestCase):
    def test_extract_model_structure_three_stage(self) -> None:
        text = (
            "The Group applies IFRS 9 with Stage 1, Stage 2 and Stage 3. "
            "Credit risk is assessed using segmentation by arrears buckets."
        )
        field = _extract_model_structure(text, "https://example.com")
        self.assertIn("3-stage IFRS 9 model", field.value or "")

    def test_extract_scenario_weights(self) -> None:
        text = (
            "Expected credit losses use four scenarios: base, upside, downside and severe downside "
            "with weights 40%, 30%, 25% and 5%."
        )
        field = _extract_scenario_design(text, "https://example.com")
        self.assertIn("4 scenarios: Base, Upside, Downside, Extreme", field.value or "")
        self.assertIn("weights: 40/30/25/5", field.value or "")

    def test_extract_core_metrics_prefers_provision_line(self) -> None:
        table = TableData(
            title="Core",
            columns=["Row", "Value 1", "Value 2"],
            rows=[
                ["the period, net reversal of provisions amounted to £", "8.8", ""],
                ["provision for expected credit loss). At", "27", "2025"],
                ["trade receivables with a gross value of £", "254.9", ""],
                ["balance sheet, less a provision for impairment of £", "73.2", ""],
            ],
            source_url="https://example.com",
        )
        gross, allowance, _ = _extract_core_metrics("", [table])
        self.assertEqual(gross, 254.9)
        self.assertEqual(allowance, -73.2)


if __name__ == "__main__":
    unittest.main()
