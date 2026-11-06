from __future__ import annotations

import csv
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image

from parallax_core42 import AXES, FAMILIES, OUTPUT_COLUMNS, SCHEMA_ID, ExtractorConfig, load_target, measure_path, measure_rgb
from parallax_core42.cli import main as cli_main


ROOT = Path(__file__).resolve().parent.parent
# Reference platform macOS arm64: 1e-10. Linux x86_64 differs by up to ~1.4e-8 relative; CI sets 1e-7 there.
RTOL = float(__import__("os").environ.get("CORE42_KNOWN_ANSWER_RTOL", "1e-10"))
FIXTURE = ROOT / "examples" / "synthetic_histology_fixture.png"
RAW_EXPECTED = ROOT / "examples" / "example_output.jsonl"
NORM_EXPECTED = ROOT / "examples" / "example_output_fixed_macenko.jsonl"
TARGET = ROOT / "references" / "tcga_fixed_macenko_target.json"


def load_row(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8").strip())


class Core42KnownAnswer(unittest.TestCase):
    def assert_row_close(self, observed: dict[str, object], expected: dict[str, object]) -> None:
        self.assertEqual(tuple(observed), OUTPUT_COLUMNS)
        self.assertEqual(observed["schema_id"], SCHEMA_ID)
        self.assertEqual(observed["status"], "ok")
        for column in OUTPUT_COLUMNS:
            if column in AXES:
                self.assertTrue(
                    (np.isnan(float(observed[column])) and np.isnan(float(expected[column]))) or abs(float(observed[column]) - float(expected[column])) <= RTOL * max(1.0, abs(float(expected[column]))),
                    msg=f"{column}: observed={observed[column]} expected={expected[column]}",
                )
            else:
                self.assertEqual(observed[column], expected[column], msg=column)

    def test_schema_is_exact(self) -> None:
        self.assertEqual(len(AXES), 42)
        self.assertEqual(len(set(AXES)), 42)
        self.assertEqual(tuple(axis for family in FAMILIES.values() for axis in family), AXES)

    def test_fixture_hash_is_frozen(self) -> None:
        digest = hashlib.sha256(FIXTURE.read_bytes()).hexdigest()
        self.assertEqual(digest, "35e83fb7f64d0b1ee02d1ffe1cd55ec94e6d658dd02db03efa5b61a58c01f827")

    def test_raw_known_answer(self) -> None:
        self.assert_row_close(measure_path(FIXTURE), load_row(RAW_EXPECTED))

    def test_fixed_macenko_known_answer(self) -> None:
        rgb = np.asarray(Image.open(FIXTURE).convert("RGB"))
        normalized = load_target(TARGET).transform(rgb)
        self.assert_row_close(measure_rgb(normalized, source_id=FIXTURE.name), load_row(NORM_EXPECTED))

    def test_repeat_is_deterministic(self) -> None:
        first = measure_path(FIXTURE)
        second = measure_path(FIXTURE)
        self.assertEqual(json.dumps(first, sort_keys=True, allow_nan=True), json.dumps(second, sort_keys=True, allow_nan=True))

    def test_nondefault_configuration_is_rejected(self) -> None:
        rgb = np.asarray(Image.open(FIXTURE).convert("RGB"))
        with self.assertRaisesRegex(ValueError, "constants are frozen"):
            measure_rgb(rgb, config=ExtractorConfig(void_threshold=0.20))

    def test_cli_csv_schema(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "result.csv"
            self.assertEqual(cli_main([str(FIXTURE), "--output", str(output)]), 0)
            with output.open(newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(len(rows), 1)
            self.assertEqual(tuple(rows[0]), OUTPUT_COLUMNS)
            self.assertEqual(rows[0]["status"], "ok")

    def test_cli_error_row_preserves_schema(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            bad = Path(temporary) / "not_an_image.png"
            bad.write_text("not an image", encoding="utf-8")
            output = Path(temporary) / "error.csv"
            self.assertEqual(cli_main([str(bad), "--output", str(output)]), 1)
            with output.open(newline="", encoding="utf-8") as handle:
                row = next(csv.DictReader(handle))
            self.assertEqual(row["schema_id"], SCHEMA_ID)
            self.assertEqual(row["status"], "error")


if __name__ == "__main__":
    unittest.main()
