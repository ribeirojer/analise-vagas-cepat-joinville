import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "pipeline"))
import pipeline as pl  # noqa: E402

GOLDEN = Path(__file__).resolve().parent / "golden"
DATES = {
    "2026-01-05": "05012026",
    "2026-01-12": "12012026",
    "2026-01-19": "19012026",
    "2026-01-26": "26012026",
}


def assert_json_close(test: unittest.TestCase, expected, actual, path=""):
    if isinstance(expected, dict):
        test.assertIsInstance(actual, dict, path)
        test.assertEqual(set(expected), set(actual), path)
        for key in expected:
            assert_json_close(test, expected[key], actual[key], f"{path}/{key}")
    elif isinstance(expected, list):
        test.assertIsInstance(actual, list, path)
        test.assertEqual(len(expected), len(actual), path)
        for index, (a, b) in enumerate(zip(expected, actual)):
            assert_json_close(test, a, b, f"{path}[{index}]")
    elif isinstance(expected, (int, float)) and not isinstance(expected, bool):
        test.assertIsInstance(actual, (int, float), path)
        test.assertAlmostEqual(float(expected), float(actual), places=6, msg=path)
    else:
        test.assertEqual(expected, actual, path)


class JanGoldenIntegrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not pl.Ocr().bin:
            raise unittest.SkipTest("Tesseract não encontrado")
        cls.tmp = tempfile.TemporaryDirectory(prefix="cepat_test_")
        base = Path(cls.tmp.name)
        pdfs = base / "pdfs"
        pdfs.mkdir()
        for iso in DATES:
            shutil.copy(ROOT / "pdfs" / "2026" / f"{iso}.pdf", pdfs)
        out = base / "out"
        cache = base / "cache"
        proc = subprocess.run(
            [
                sys.executable,
                str(ROOT / "pipeline" / "pipeline.py"),
                "--pdfs",
                str(pdfs),
                "--out",
                str(out),
                "--cache",
                str(cache),
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            raise AssertionError(
                "Falha no pipeline:\n" + (proc.stdout + proc.stderr)[-4000:]
            )
        cls.out = out

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_occupations_output(self):
        occupations = json.loads(
            (self.out / "occupations-2026.json").read_text()
        )
        self.assertIn("05/01/2026", occupations)
        self.assertIn("acumulado", occupations)
        top = occupations["05/01/2026"][0]
        self.assertGreater(top["vagas"], 0)
        self.assertTrue(top["cbo"])
        self.assertIn("median", top)

    def test_january_matches_golden(self):
        for iso, compact in DATES.items():
            with self.subTest(date=iso):
                generated = json.loads(
                    (
                        self.out
                        / f"summary-Lista-de-Vagas-de-Emprego-{compact}.json"
                    ).read_text()
                )
                expected = json.loads(
                    (GOLDEN / f"summary-{compact}.json").read_text()
                )
                assert_json_close(self, expected, generated)


if __name__ == "__main__":
    unittest.main()
