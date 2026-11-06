"""The cohort fingerprint example reproduces the shipped TCGA route result and survives edge cases."""
from __future__ import annotations

import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "examples" / "fingerprint_cohort.py"
DATA = ROOT / "examples" / "tcga_route_fingerprint" / "tile_measurements_raw.csv"
HAVE_EXTRAS = all(importlib.util.find_spec(m) for m in ("pandas", "sklearn", "matplotlib"))


@unittest.skipUnless(HAVE_EXTRAS, "examples extras not installed")
class FingerprintCohort(unittest.TestCase):
    def run_script(self, csv: Path, out: Path) -> str:
        r = subprocess.run([sys.executable, str(SCRIPT), str(csv), "--group", "route", "--unit", "patient", "--out", str(out)],
                           capture_output=True, text=True, check=False, cwd=ROOT,
                           env={"PYTHONPATH": str(ROOT / "src"), "PATH": ""})
        self.assertEqual(r.returncode, 0, r.stderr)
        return (out / "summary.txt").read_text()

    def test_reproduces_shipped_result(self):
        with tempfile.TemporaryDirectory() as d:
            s = self.run_script(DATA, Path(d))
        self.assertIn("balanced accuracy 0.977", s)
        self.assertIn("other-sites vs AA-regular: 11/42", s)

    def test_single_unit_group_and_empty_axis(self):
        import numpy as np
        import pandas as pd

        t = pd.read_csv(DATA)
        one = t[t.route == "AA-derivative"].patient.unique()[0]
        t = t[(t.route != "AA-derivative") | (t.patient == one)].copy()
        t["gamma"] = np.nan
        with tempfile.TemporaryDirectory() as d:
            csv = Path(d) / "edge.csv"
            t.to_csv(csv, index=False)
            s = self.run_script(csv, Path(d) / "out")
        self.assertIn("left out: gamma", s)
        self.assertIn("LDA uses groups with two or more units only; left out: AA-derivative", s)


if __name__ == "__main__":
    unittest.main()
