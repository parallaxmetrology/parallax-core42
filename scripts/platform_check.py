#!/usr/bin/env python3
"""Report, axis by axis, how this platform's output differs from the recorded known answers.

Never fails: it is a diagnostic for comparing numerical platforms (OS, CPU, BLAS,
library versions). The known answers were recorded on macOS arm64.
"""
from __future__ import annotations

import json
import platform
from pathlib import Path

import numpy as np
import scipy
import skimage
from PIL import Image

from parallax_core42 import AXES, load_target, measure_path, measure_rgb

ROOT = Path(__file__).resolve().parent.parent
FIX = ROOT / "examples" / "synthetic_histology_fixture.png"


def diffs(observed: dict, expected: dict) -> dict:
    out = {}
    for ax in AXES:
        o, e = float(observed[ax]), float(expected[ax])
        out[ax] = {"observed": o, "expected": e, "abs": abs(o - e), "rel": abs(o - e) / max(1.0, abs(e))}
    return out


def main() -> None:
    raw = diffs(measure_path(FIX), json.loads((ROOT / "examples" / "example_output.jsonl").read_text().strip()))
    norm_img = load_target(ROOT / "references" / "tcga_fixed_macenko_target.json").transform(np.asarray(Image.open(FIX).convert("RGB")))
    nrm = diffs(measure_rgb(norm_img), json.loads((ROOT / "examples" / "example_output_fixed_macenko.jsonl").read_text().strip()))
    env = {"platform": platform.platform(), "machine": platform.machine(), "python": platform.python_version(),
           "numpy": np.__version__, "scipy": scipy.__version__, "scikit_image": skimage.__version__}
    print(json.dumps(env))
    for name, d in (("raw", raw), ("fixed_macenko", nrm)):
        worst = sorted(d.items(), key=lambda kv: -kv[1]["rel"])
        print(f"{name}: max relative difference {worst[0][1]['rel']:.3e} ({worst[0][0]}); axes above 1e-10: {sum(v['rel'] > 1e-10 for v in d.values())}/42")
        for ax, v in worst[:8]:
            print(f"  {ax:24s} expected {v['expected']:.12g}  observed {v['observed']:.12g}  rel {v['rel']:.3e}")


if __name__ == "__main__":
    main()
