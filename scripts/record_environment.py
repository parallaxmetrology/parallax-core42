#!/usr/bin/env python3
"""Record the validation environment without machine-specific paths."""

from __future__ import annotations

import json
import platform
import sys
from pathlib import Path

import numpy
import scipy
import skimage
from PIL import Image


ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    payload = {
        "python": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "platform_system": platform.system(),
        "platform_release": platform.release(),
        "machine": platform.machine(),
        "numpy": numpy.__version__,
        "scipy": scipy.__version__,
        "scikit_image": skimage.__version__,
        "pillow": Image.__version__,
        "byteorder": sys.byteorder,
    }
    output = ROOT / "validation" / "BUILD_ENVIRONMENT.json"
    output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
