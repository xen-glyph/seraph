import importlib.util
import tempfile
import unittest
from datetime import datetime
from decimal import Decimal
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "bullet_lube_calculator.py"
SPEC = importlib.util.spec_from_file_location("bullet_lube_calculator", MODULE_PATH)
calculator = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(calculator)


class CalculationTests(unittest.TestCase):
    def test_two_pound_sixty_forty_recipe(self):
        total_grams, rows = calculator.calculate_rows(
            Decimal("2"),
            "lb",
            [("Beeswax", Decimal("60")), ("Lard", Decimal("40"))],
        )

        self.assertEqual(total_grams, Decimal("907.184740"))
        self.assertEqual(rows[0][2], Decimal("544.3108440"))
        self.assertEqual(rows[1][2], Decimal("362.8738960"))
        self.assertEqual(calculator.format_weight(rows[0][2], "lb"), "1.2 lb")
        self.assertEqual(calculator.format_weight(rows[1][2], "oz"), "12.8 oz")

    def test_report_stays_inside_76_columns(self):
        lines = calculator.build_report_lines(
            "Standard Bullet Lube",
            Decimal("2"),
            "lb",
            [("Beeswax", Decimal("60")), ("Lard", Decimal("40"))],
            prepared_at=datetime(2026, 8, 7, 12, 0),
        )
        self.assertTrue(lines)
        self.assertTrue(all(len(line) <= 76 for line in lines))

    def test_default_export_filename(self):
        filename = calculator.default_export_filename(
            "Ol' Sawtooth Moose's Standard Bullet Lube",
            Decimal("2"),
            "lb",
        )
        self.assertEqual(
            filename,
            "ol-sawtooth-moose-s-standard-bullet-lube-2-lb.txt",
        )

    def test_report_can_be_written_as_utf8_text(self):
        report = "\n".join(
            calculator.build_report_lines(
                "Test Recipe",
                Decimal("100"),
                "g",
                [("Wax", Decimal("50")), ("Oil", Decimal("50"))],
                prepared_at=datetime(2026, 8, 7, 12, 0),
            )
        ) + "\n"

        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "recipe.txt"
            output.write_text(report, encoding="utf-8")
            loaded = output.read_text(encoding="utf-8")

        self.assertIn("BULLET LUBE RECIPE", loaded)
        self.assertIn("Wax", loaded)
        self.assertIn("50 g", loaded)


if __name__ == "__main__":
    unittest.main()
