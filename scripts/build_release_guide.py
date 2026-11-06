#!/usr/bin/env python3
"""Build the self-contained HTML release guide from canonical Markdown files."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SOURCES = [
    ROOT / "README.md",
    ROOT / "docs" / "SCOPE_AND_BOUNDARIES.md",
    ROOT / "docs" / "AXIS_DICTIONARY.md",
    ROOT / "docs" / "PREPROCESSING_AND_SCALE.md",
    ROOT / "docs" / "PROVENANCE.md",
    ROOT / "docs" / "VALIDATION.md",
]
OUTPUT = ROOT / "PARALLAX_CORE42_RELEASE_GUIDE.html"


def main() -> None:
    pandoc = shutil.which("pandoc")
    if pandoc is None:
        raise RuntimeError("pandoc is required to rebuild the HTML guide")
    subprocess.run(
        [
            pandoc,
            *map(str, SOURCES),
            "--standalone",
            "--toc",
            "--toc-depth=2",
            "--metadata",
            "title=Parallax Core 42 v1.0.0 — Release Guide",
            "--css",
            str(ROOT / "docs" / "release.css"),
            "--embed-resources",
            "--output",
            str(OUTPUT),
        ],
        check=True,
    )
    print(OUTPUT)


if __name__ == "__main__":
    main()
