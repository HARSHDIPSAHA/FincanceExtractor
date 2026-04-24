import unittest

from ifrs9_benchmark.extract import (
    _extract_ageing_table,
    _extract_core_metrics,
    _extract_impairment_movement_table,
    _extract_model_structure,
    _extract_scenario_design,
    _parse_ageing_buckets,
    _parse_stage_movements,
)
from ifrs9_benchmark.models import AgeingBucket, StageMovement, TableData
from ifrs9_benchmark.utils import parse_number, safe_ratio


class UtilsTests(unittest.TestCase):
    def test_parse_number_parentheses(self) -> None:
        self.assertEqual(parse_number("(207.4)"), -207.4)
        self.assertEqual(parse_number("1,550.7"), 1550.7)

    def test_safe_ratio(self) -> None:
        self.assertAlmostEqual(safe_ratio(207.4, 1477.8), 0.1403437542, places=9)


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


class AgeingTableTests(unittest.TestCase):
    def test_parse_ageing_buckets_basic(self) -> None:
        table = TableData(
            title="Ageing",
            columns=["Bucket", "Gross", "Allowance"],
            rows=[
                ["Not past due", "194.6", "(10.0)"],
                ["0-60 days past due", "25.0", "(2.0)"],
                ["60-120 days past due", "7.7", "(1.5)"],
                ["120+ days past due", "27.6", "(15.0)"],
            ],
            source_url="https://example.com",
        )
        buckets = _parse_ageing_buckets(table)
        self.assertEqual(len(buckets), 4)
        self.assertEqual(buckets[0].bucket_name, "Not Past Due")
        self.assertAlmostEqual(buckets[0].gross_amount, 194.6)
        self.assertEqual(buckets[3].bucket_name, "120+ Days")
        self.assertAlmostEqual(buckets[3].gross_amount, 27.6)

    def test_extract_ageing_table_detection(self) -> None:
        tables = [
            TableData(
                title="Other",
                columns=["A", "B"],
                rows=[["Revenue", "100"]],
                source_url="https://example.com",
            ),
            TableData(
                title="Ageing",
                columns=["Status", "Amount"],
                rows=[
                    ["Not past due", "194.6"],
                    ["0-60 days", "25.0"],
                    ["60-120 days", "7.7"],
                    ["120+ days", "27.6"],
                ],
                source_url="https://example.com",
            ),
        ]
        result = _extract_ageing_table(tables)
        self.assertIsNotNone(result)
        self.assertEqual(result.title, "Ageing")


class ImpairmentMovementTests(unittest.TestCase):
    def test_parse_stage_movements(self) -> None:
        table = TableData(
            title="Movement",
            columns=["Stage", "Opening", "Charge", "Write-offs", "Closing"],
            rows=[
                ["Stage 1 opening balance", "(17.7)", "", "", ""],
                ["Stage 1 impairment charge", "", "(6.3)", "", ""],
                ["Stage 1 write-offs", "", "", "6.0", ""],
                ["Stage 1 closing balance", "(11.7)", "", "", ""],
                ["Stage 2 opening balance", "(18.9)", "", "", ""],
                ["Stage 2 impairment charge", "", "(6.3)", "", ""],
                ["Stage 2 write-offs", "", "", "7.9", ""],
                ["Stage 2 closing balance", "(17.3)", "", "", ""],
                ["Stage 3 opening balance", "(44.1)", "", "", ""],
                ["Stage 3 impairment charge", "", "(18.2)", "", ""],
                ["Stage 3 write-offs", "", "", "18.1", ""],
                ["Stage 3 closing balance", "(44.2)", "", "", ""],
            ],
            source_url="https://example.com",
        )
        movements = _parse_stage_movements(table)
        self.assertEqual(len(movements), 3)

        stage3 = next(m for m in movements if m.stage == "Stage 3")
        self.assertAlmostEqual(stage3.opening, -44.1)
        self.assertAlmostEqual(stage3.charge, -18.2)
        self.assertAlmostEqual(stage3.write_offs, 18.1)
        self.assertAlmostEqual(stage3.closing, -44.2)

    def test_extract_impairment_table_detection(self) -> None:
        tables = [
            TableData(
                title="Other",
                columns=["A", "B"],
                rows=[["Revenue", "100"]],
                source_url="https://example.com",
            ),
            TableData(
                title="Impairment Movement",
                columns=["Stage", "Opening", "Charge", "Closing"],
                rows=[
                    ["Stage 1 opening", "(17.7)", "", ""],
                    ["Stage 2 opening", "(18.9)", "", ""],
                    ["Stage 3 opening", "(44.1)", "", ""],
                ],
                source_url="https://example.com",
            ),
        ]
        result = _extract_impairment_movement_table(tables)
        self.assertIsNotNone(result)
        self.assertEqual(result.title, "Impairment Movement")


if __name__ == "__main__":
    unittest.main()
