#!/usr/bin/env python3
"""Development-time pixel equivalence check for the corrected normalizer."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np
from PIL import Image

from parallax_core42 import load_target


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--historical-runner", type=Path, required=True)
    parser.add_argument("--target", type=Path, required=True)
    parser.add_argument("--image", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    spec = importlib.util.spec_from_file_location("parallax_historical_runner", args.historical_runner)
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not import historical runner")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    target = json.loads(args.target.read_text(encoding="utf-8"))
    historical = module.MacenkoNormalizerFixed()
    historical.stain_matrix_target = np.asarray(target["stain_matrix_target"], dtype=float)
    historical.maxC_target = np.asarray(target["maxC_target"], dtype=float)
    rgb = np.asarray(Image.open(args.image).convert("RGB"))
    expected = historical.transform(rgb)
    observed = load_target(args.target).transform(rgb)
    difference = np.abs(expected.astype(np.int16) - observed.astype(np.int16))
    payload = {
        "status": "PASS" if np.array_equal(expected, observed) else "FAIL",
        "historical_runner_sha256": sha256(args.historical_runner),
        "target_sha256": sha256(args.target),
        "image_sha256": sha256(args.image),
        "pixels_compared": int(expected.size),
        "different_channel_values": int(np.count_nonzero(difference)),
        "maximum_absolute_channel_difference": int(difference.max()),
        "boundary": "Pixel equivalence for one fixed input and target; not evidence of stain invariance.",
    }
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2))
    raise SystemExit(0 if payload["status"] == "PASS" else 1)


if __name__ == "__main__":
    main()
