#!/usr/bin/env python3
"""Independent structural and known-answer validation for the release packet."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from parallax_core42 import AXES, OUTPUT_COLUMNS, SCHEMA_ID, VERSION, ExtractorConfig, measure_path, measure_rgb  # noqa: E402


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# Known answers were recorded on macOS arm64, where they reproduce exactly. Other
# platforms differ at the floating-point level (up to about 1.4e-8 relative on Linux
# x86_64); set CORE42_KNOWN_ANSWER_RTOL=1e-7 there. See docs/KNOWN_ISSUES.md.
KNOWN_ANSWER_RTOL = float(__import__("os").environ.get("CORE42_KNOWN_ANSWER_RTOL", "1e-10"))


def require(condition: bool, name: str, checks: list[str]) -> None:
    if not condition:
        raise AssertionError(name)
    checks.append(name)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check-only", action="store_true", help="validate without rewriting validation/RELEASE_VALIDATION.json")
    args = parser.parse_args()
    checks: list[str] = []
    fixture = ROOT / "examples" / "synthetic_histology_fixture.png"
    expected = json.loads((ROOT / "examples" / "example_output.jsonl").read_text().strip())
    observed = measure_path(fixture)
    require(len(AXES) == 42 and len(set(AXES)) == 42, "schema contains 42 unique axes", checks)
    require(tuple(observed) == OUTPUT_COLUMNS, "output order matches schema", checks)
    require(observed["schema_id"] == SCHEMA_ID and observed["status"] == "ok", "fixture measures successfully", checks)
    require(sha256(fixture) == "35e83fb7f64d0b1ee02d1ffe1cd55ec94e6d658dd02db03efa5b61a58c01f827", "fixture hash matches", checks)
    release = json.loads((ROOT / "RELEASE.json").read_text())
    require(release["version"] == VERSION and release["schema_id"] == SCHEMA_ID, "release metadata matches package identity", checks)
    require(release["axis_count"] == len(AXES), "release metadata axis count matches schema", checks)
    try:
        measure_rgb(__import__("numpy").zeros((64, 64, 3), dtype="uint8"), config=ExtractorConfig(void_threshold=0.20))
    except ValueError as exc:
        require("constants are frozen" in str(exc), "nondefault measurement configuration is rejected", checks)
    else:
        raise AssertionError("nondefault measurement configuration is rejected")
    for axis in AXES:
        difference = abs(float(observed[axis]) - float(expected[axis]))
        require(difference <= KNOWN_ANSWER_RTOL * max(1.0, abs(float(expected[axis]))), f"known answer matches: {axis}", checks)

    with (ROOT / "docs" / "AXIS_DICTIONARY.csv").open(newline="", encoding="utf-8") as handle:
        dictionary = list(csv.DictReader(handle))
    require([row["axis"] for row in dictionary] == list(AXES), "axis dictionary matches schema and order", checks)
    require(all(row["definition"] and row["reported_unit"] and row["caution"] for row in dictionary), "axis dictionary fields are complete", checks)

    equivalence = json.loads((ROOT / "validation" / "HISTORICAL_SOURCE_EQUIVALENCE.json").read_text())
    require(equivalence["status"] == "PASS", "historical source-equivalence status is PASS", checks)
    require(equivalence["axes_matching_at_1e-12"] == 42, "all 42 axes match historical source", checks)
    require(equivalence["maximum_absolute_difference"] == 0.0, "historical maximum difference is zero", checks)
    require(equivalence["historical_kernel_sha256"] == "b6fc19229b98f854c95bfcb1c3ebb8040cd935303ec1be0cbf1349d14d30a43e", "historical source hash is pinned", checks)
    real_equivalence = json.loads((ROOT / "validation" / "HISTORICAL_SOURCE_EQUIVALENCE_REAL_HE.json").read_text())
    require(real_equivalence["status"] == "PASS", "real H&E source-equivalence status is PASS", checks)
    require(real_equivalence["axes_matching_at_1e-12"] == 42, "all 42 axes match historical source on real H&E", checks)
    require(real_equivalence["maximum_absolute_difference"] == 0.0, "real H&E historical maximum difference is zero", checks)

    target = json.loads((ROOT / "references" / "tcga_fixed_macenko_target.json").read_text())
    require(target["source_record_sha256"] == "d2f71ff6bb3d02f86f3d2700a394a1a28fb89adb907258afb1f3b30de2b983ef", "normalizer source-record hash is pinned", checks)
    require(len(target["stain_matrix_target"]) == 2 and all(len(row) == 3 for row in target["stain_matrix_target"]), "normalizer target is 2x3", checks)
    require(len(target["maxC_target"]) == 2, "normalizer concentration target has two values", checks)
    normalizer_equivalence = json.loads((ROOT / "validation" / "NORMALIZER_SOURCE_EQUIVALENCE.json").read_text())
    require(normalizer_equivalence["status"] == "PASS", "normalizer source-equivalence status is PASS", checks)
    require(normalizer_equivalence["different_channel_values"] == 0, "normalizer output is pixel-identical to source", checks)
    require(normalizer_equivalence["historical_runner_sha256"] == "566bdb05ae2bf92d52d450d3bd0eab64e42784554066859d903e713c6bc4d6ff", "normalizer source hash is pinned", checks)

    environment = json.loads((ROOT / "validation" / "BUILD_ENVIRONMENT.json").read_text())
    require(all(environment.get(key) for key in ["python", "numpy", "scipy", "scikit_image", "pillow"]), "build environment is recorded", checks)
    packaging = json.loads((ROOT / "validation" / "PACKAGING_VALIDATION.json").read_text())
    wheel = ROOT / packaging["wheel"]
    require(packaging["status"] == "PASS" and wheel.is_file(), "wheel packaging validation is PASS", checks)
    require(sha256(wheel) == packaging["wheel_sha256"], "wheel hash matches packaging record", checks)
    require(packaging["byte_identical_to_expected"] is True, "installed-wheel smoke output is byte-identical", checks)

    source_text = "\n".join(path.read_text(encoding="utf-8") for path in (ROOT / "src").rglob("*.py"))
    require("/Users/" not in source_text and "/content/" not in source_text, "executable package has no machine-specific paths", checks)
    require("OMEGA_REF" not in source_text and "class_label" not in source_text, "measurement package has no reference or label dependency", checks)

    process = subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", str(ROOT / "tests"), "-v"],
        cwd=ROOT,
        env={**dict(__import__("os").environ), "PYTHONPATH": str(SRC)},
        capture_output=True,
        text=True,
    )
    require(process.returncode == 0, "unit and CLI tests pass", checks)

    payload = {
        "status": "PASS",
        "checks_passed": len(checks),
        "checks": checks,
        "schema_id": SCHEMA_ID,
        "axis_count": len(AXES),
        "historical_source_equivalence": equivalence,
        "historical_source_equivalence_real_he": real_equivalence,
        "normalizer_source_equivalence": normalizer_equivalence,
        "build_environment": environment,
        "packaging_validation": packaging,
        "test_suite": "Python unittest discovery completed successfully, including schema, raw and normalized known answers, repeat determinism, frozen-config rejection, and CLI success/error paths.",
        "boundary": "Software and numerical validation only; no diagnostic, prognostic, biological, or external-performance claim is created by this release.",
    }
    if not args.check_only:
        output = ROOT / "validation" / "RELEASE_VALIDATION.json"
        output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": payload["status"], "checks_passed": len(checks), "axis_count": len(AXES)}, indent=2))


if __name__ == "__main__":
    main()
