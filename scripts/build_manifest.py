#!/usr/bin/env python3
"""Build the SHA-256 release manifest."""

from __future__ import annotations

import hashlib
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "MANIFEST_SHA256.txt"


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def main() -> None:
    files = sorted(
        path for path in ROOT.rglob("*")
        if path.is_file()
        and path != OUTPUT
        and "__pycache__" not in path.parts
        and not any(part in {".git", ".pytest_cache", ".ruff_cache", ".venv"} or part.endswith(".egg-info") for part in path.parts)
        and not path.name.endswith(".pyc")
    )
    OUTPUT.write_text(
        "".join(f"{digest(path)}  {path.relative_to(ROOT)}\n" for path in files),
        encoding="utf-8",
    )
    print(f"wrote {OUTPUT} with {len(files)} files")


if __name__ == "__main__":
    main()
