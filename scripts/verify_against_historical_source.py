#!/usr/bin/env python3
"""Development-time equivalence check against the archived v4.1 kernel.

The historical file is not bundled. This script records a comparison when its path
is supplied; the installed release uses the self-contained known-answer test.
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path

import numpy as np

from parallax_core42 import AXES, measure_path


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--historical-kernel", type=Path, required=True)
    parser.add_argument("--image", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    spec = importlib.util.spec_from_file_location("parallax_historical_v41", args.historical_kernel)
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not import historical kernel")
    module = importlib.util.module_from_spec(spec)
    with contextlib.redirect_stdout(io.StringIO()):
        spec.loader.exec_module(module)
    module.BATCH_CFG["OMEGA_REF_PATH"] = ""
    module.BATCH_CFG["RESIZE_LONG_EDGE"] = 512
    with contextlib.redirect_stdout(io.StringIO()):
        expected = module.analyse_image(args.image)
    observed = measure_path(args.image)
    differences = {
        axis: abs(float(expected[axis]) - float(observed[axis]))
        for axis in AXES
        if np.isfinite(float(expected[axis])) and np.isfinite(float(observed[axis]))
    }
    matches = {
        axis: bool(np.isclose(float(expected[axis]), float(observed[axis]), rtol=1e-12, atol=1e-12, equal_nan=True))
        for axis in AXES
    }
    payload = {
        "status": "PASS" if all(matches.values()) else "FAIL",
        "historical_kernel_sha256": sha256(args.historical_kernel),
        "image_sha256": sha256(args.image),
        "axes_compared": len(AXES),
        "axes_matching_at_1e-12": sum(matches.values()),
        "maximum_absolute_difference": max(differences.values(), default=0.0),
        "mismatches": [axis for axis, match in matches.items() if not match],
        "boundary": "Numerical source equivalence only; it does not validate biological meaning or external performance.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2))
    raise SystemExit(0 if payload["status"] == "PASS" else 1)


if __name__ == "__main__":
    main()
