from __future__ import annotations

import importlib.util
import sys
import unittest
from decimal import Decimal
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "cast_bullet_workshop_calculator.py"
SPEC = importlib.util.spec_from_file_location("cast_bullet_workshop_calculator", MODULE_PATH)
assert SPEC and SPEC.loader
cbwc = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = cbwc
SPEC.loader.exec_module(cbwc)


class AlloyPresetTests(unittest.TestCase):
    def test_all_builtin_alloys_total_100_percent(self) -> None:
        for name, alloy in cbwc.BUILTIN_ALLOYS.items():
            with self.subTest(name=name):
                components = cbwc.alloy_components(alloy)
                total = sum((percent for _, percent in components), Decimal("0"))
                self.assertEqual(total, Decimal("100"))

    def test_20_to_1_uses_exact_parts_math(self) -> None:
        components = dict(cbwc.alloy_components(cbwc.BUILTIN_ALLOYS["20:1 Lead/Tin"]))
        self.assertEqual(components["Lead"], Decimal("2000") / Decimal("21"))
        self.assertEqual(components["Tin"], Decimal("100") / Decimal("21"))
        total_grams, rows = cbwc.calculate_rows(
            Decimal("21"),
            "lb",
            list(components.items()),
        )
        row_map = {name: grams / cbwc.GRAMS_PER_UNIT["lb"] for name, _, grams in rows}
        self.assertEqual(row_map["Lead"], Decimal("20"))
        self.assertEqual(row_map["Tin"], Decimal("1"))
        self.assertEqual(total_grams / cbwc.GRAMS_PER_UNIT["lb"], Decimal("21"))


class BlendTests(unittest.TestCase):
    def setUp(self) -> None:
        self.sources = cbwc.all_source_alloys(cbwc.default_store())

    def target(self, name: str):
        return cbwc.component_list_to_metal_composition(
            cbwc.alloy_components(cbwc.BUILTIN_ALLOYS[name])
        )

    def test_equal_lead_and_linotype_make_hardball(self) -> None:
        weights, final = cbwc.solve_blend(
            self.target("Hardball"),
            Decimal("20"),
            ["Pure Lead", "Linotype 84/4/12"],
            self.sources,
        )
        self.assertEqual(weights, [Decimal("10"), Decimal("10")])
        self.assertEqual(final, {"Pb": Decimal("92"), "Sn": Decimal("2"), "Sb": Decimal("6")})

    def test_three_sources_make_lyman_number_two(self) -> None:
        weights, final = cbwc.solve_blend(
            self.target("Lyman No. 2"),
            Decimal("20"),
            ["Pure Lead", "Pure Tin", "SuperHard 70/30"],
            self.sources,
        )
        self.assertAlmostEqual(float(weights[0]), 15.6666666667, places=8)
        self.assertEqual(weights[1], Decimal("1"))
        self.assertAlmostEqual(float(weights[2]), 3.3333333333, places=8)
        for symbol, expected in {"Pb": 90, "Sn": 5, "Sb": 5}.items():
            self.assertAlmostEqual(float(final[symbol]), expected, places=8)

    def test_negative_solution_is_rejected(self) -> None:
        target = {"Pb": Decimal("80"), "Sn": Decimal("20"), "Sb": Decimal("0")}
        with self.assertRaises(ValueError):
            cbwc.solve_blend(
                target,
                Decimal("10"),
                ["Pure Lead", "Antimonial Lead 94/6"],
                self.sources,
            )


class ReportTests(unittest.TestCase):
    def test_report_stays_within_76_columns(self) -> None:
        spec = cbwc.ReportSpec(
            report_title="Cast Bullet Alloy Recipe",
            recipe_name="20:1 Lead/Tin",
            total_amount=Decimal("21"),
            input_unit="lb",
            rows=cbwc.alloy_components(cbwc.BUILTIN_ALLOYS["20:1 Lead/Tin"]),
            info_lines=["Exact traditional parts-ratio calculation."],
        )
        lines = cbwc.build_report_lines(spec)
        self.assertTrue(all(len(line) <= cbwc.HEADER_WIDTH for line in lines))

    def test_print_document_has_two_leading_blank_lines_by_default(self) -> None:
        spec = cbwc.ReportSpec(
            report_title="Bullet Lube Recipe",
            recipe_name="Test",
            total_amount=Decimal("1"),
            input_unit="lb",
            rows=[("Beeswax", Decimal("60")), ("Lard", Decimal("40"))],
        )
        document = cbwc.prepare_print_text(spec, cbwc.DEFAULT_LEADING_BLANK_LINES)
        self.assertTrue(document.startswith("\n\n" + "—" * cbwc.HEADER_WIDTH))


if __name__ == "__main__":
    unittest.main()
