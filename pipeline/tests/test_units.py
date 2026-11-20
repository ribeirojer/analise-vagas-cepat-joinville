import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pipeline as pl  # noqa: E402


class SalaryParsingTest(unittest.TestCase):
    def test_monthly(self):
        self.assertAlmostEqual(pl.parse_salary("R$ 1.518,00"), 1518.0)
        self.assertAlmostEqual(pl.parse_salary("R$ 2.442,26"), 2442.26)
        self.assertAlmostEqual(pl.parse_salary("R$2.873,00"), 2873.0)

    def test_hourly(self):
        self.assertAlmostEqual(pl.parse_salary("R$ 9,32/h"), 1845.36)
        self.assertAlmostEqual(pl.parse_salary("R$ 30,00/h"), 5940.0)

    def test_daily(self):
        self.assertAlmostEqual(pl.parse_salary("R$ 125,00/dia"), 2750.0)
        self.assertAlmostEqual(pl.parse_salary("R$ 250/dia"), 5500.0)

    def test_ocr_variants(self):
        self.assertAlmostEqual(pl.parse_salary("R$ 2.11200"), 2112.0)
        self.assertAlmostEqual(pl.parse_salary("R$211200"), 2112.0)
        self.assertAlmostEqual(pl.parse_salary("R$ 2.53500"), 2535.0)
        self.assertAlmostEqual(pl.parse_salary("R$ 189109"), 1891.09)

    def test_missing(self):
        self.assertIsNone(pl.parse_salary("Não informado"))
        self.assertIsNone(pl.parse_salary("Não =. informado"))
        self.assertIsNone(pl.parse_salary(""))
        self.assertIsNone(pl.parse_salary(None))


class NormalizationTest(unittest.TestCase):
    def test_neighborhoods(self):
        cases = {
            "Costa João": "João Costa",
            "Garibaldi Anita": "Anita Garibaldi",
            "Cubatão Vila": "Vila Cubatão",
            "Sofia Jardim": "Jardim Sofia",
            "Garcia Adhemar": "Adhemar Garcia",
            "Zona nqustrial": "Zona Industrial Norte",
            "Zona neutral": "Zona Industrial Norte",
            "Jardim Iririú": "Iririú",
            "Araquari": "Outros",
            "Local não fixo": "Outros",
            "ras": "Outros",
            "São Marcos": "São Marcos",
        }
        for raw, expected in cases.items():
            with self.subTest(raw=raw):
                self.assertEqual(pl.normalize_bairro(raw), expected)

    def test_education(self):
        cases = {
            "Ensino Médio Completo p": "Ensino Médio Completo",
            "Ensino Completo Médio": "Ensino Médio Completo",
            "omleto": "Fundamental Completo",
            "erpleto À": "Ensino Médio Completo",
            "Estudando ou Completo": "Ensino Médio Incompleto",
            "Não Exigida": "Não exigida",
            "Fundamental ompleto": "Fundamental Completo",
            "Superior Vo incompleto": "Superior Incompleto",
            "Curso técnico ou superior incompleto": "Curso Técnico/Superior Incompleto",
        }
        for raw, expected in cases.items():
            with self.subTest(raw=raw):
                self.assertEqual(pl.normalize_education(raw), expected)


class SalaryBlockTest(unittest.TestCase):
    def setUp(self):
        self.stats = pl.salary_block([1000, 2000, 3000, 4000, 5000], 5)

    def test_quantiles(self):
        self.assertEqual(self.stats["q1"], 2000)
        self.assertEqual(self.stats["median"], 3000)
        self.assertEqual(self.stats["q3"], 4000)
        self.assertEqual(self.stats["iqr"], 2000)
        self.assertAlmostEqual(self.stats["avg"], 3000)
        self.assertAlmostEqual(self.stats["stdDev"], 1414.2135623730951)

    def test_ranges(self):
        dynamic = self.stats["dynamicRanges"]["ranges"]
        self.assertEqual(len(dynamic), 6)
        self.assertEqual(sum(r["count"] for r in dynamic), 5)
        centered = self.stats["medianCenteredRanges"]["ranges"]
        self.assertEqual([r["count"] for r in centered], [2, 1, 0, 2])
        quartile = self.stats["quartileRanges"]["ranges"]
        self.assertEqual([r["count"] for r in quartile], [2, 1, 1, 1])

    def test_outliers(self):
        self.assertEqual(self.stats["outliers"], {"low": [], "high": [], "extreme": []})


class OccupationsTest(unittest.TestCase):
    def row(self, cbo, name, vagas, salary=None, section="main"):
        return pl.Row(
            date="05/01/2026",
            page=1,
            section=section,
            code="1234567",
            cbo=cbo,
            name=name,
            vagas=vagas,
            vagas_raw=str(vagas),
            education_raw="",
            salary_raw="",
            bairro_raw="Centro",
            bairro="Centro",
            salary=salary,
        )

    def test_groups_by_cbo_and_sorts_by_vagas(self):
        rows = [
            self.row("784205", "Alimentador de linha", 10, 2000),
            self.row("784205", "Alimentador de linha", 5, 2200),
            self.row("513505", "Auxiliar de cozinha", 20, 1800),
        ]
        result = pl.occupations_summary(rows)
        self.assertEqual(result[0]["cbo"], "513505")
        self.assertEqual(result[0]["vagas"], 20)
        self.assertEqual(result[1]["cbo"], "784205")
        self.assertEqual(result[1]["vagas"], 15)
        self.assertEqual(result[1]["count"], 2)
        self.assertEqual(result[1]["median"], 2100)

    def test_excludes_ja_from_salary(self):
        rows = [
            self.row("784205", "Alimentador", 10, 2000),
            self.row("784205", "Jovem Aprendiz", 50, 1000, section="ja"),
        ]
        result = pl.occupations_summary(rows)
        self.assertEqual(result[0]["vagas"], 60)
        self.assertEqual(result[0]["median"], 2000)


class JsonComparisonTest(unittest.TestCase):
    def test_nested_numbers(self):
        # Sanidade do helper usado no teste de integração.
        self.assertTrue(pl.brl(1234.5).startswith("R$"))


if __name__ == "__main__":
    unittest.main()
