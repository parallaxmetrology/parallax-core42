"""Command-line interface for Parallax Core 42."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

from .core import ExtractorConfig, measure_rgb
from .normalization import load_target
from .schema import OUTPUT_COLUMNS, SCHEMA_ID


EXTENSIONS = {".jpg", ".jpeg", ".png", ".tif", ".tiff"}


def discover(path: Path, recursive: bool) -> list[Path]:
    if path.is_file():
        return [path]
    iterator = path.rglob("*") if recursive else path.glob("*")
    return sorted(item for item in iterator if item.is_file() and item.suffix.lower() in EXTENSIONS)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Measure the frozen Parallax Core 42 axes on RGB image patches")
    parser.add_argument("input", type=Path, help="image file or directory")
    parser.add_argument("--output", "-o", type=Path, required=True, help="output .csv or .jsonl path")
    parser.add_argument("--recursive", action="store_true", help="recurse through an input directory")
    parser.add_argument("--macenko-target", type=Path, help="optional recorded fixed-Macenko target JSON")
    args = parser.parse_args(argv)

    images = discover(args.input, args.recursive)
    if not images:
        parser.error("No supported images found")
    config = ExtractorConfig()
    normalizer = load_target(args.macenko_target) if args.macenko_target else None
    rows = []
    root = args.input if args.input.is_dir() else args.input.parent
    for path in images:
        source_id = str(path.relative_to(root))
        try:
            rgb = np.asarray(Image.open(path).convert("RGB"))
            if normalizer is not None:
                rgb = normalizer.transform(rgb)
            row = measure_rgb(rgb, source_id=source_id, config=config)
        except Exception as exc:
            row = {column: "" for column in OUTPUT_COLUMNS}
            row.update({
                "schema_id": SCHEMA_ID,
                "source_id": source_id,
                "status": "error",
                "warning": repr(exc),
                "resize_long_edge_px": config.resize_long_edge_px,
            })
        rows.append(row)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    suffix = args.output.suffix.lower()
    if suffix == ".csv":
        with args.output.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=OUTPUT_COLUMNS)
            writer.writeheader()
            writer.writerows(rows)
    elif suffix in {".jsonl", ".ndjson"}:
        with args.output.open("w", encoding="utf-8") as handle:
            for row in rows:
                handle.write(json.dumps(row, allow_nan=True, sort_keys=False) + "\n")
    else:
        parser.error("Output extension must be .csv, .jsonl, or .ndjson")

    errors = sum(row.get("status") != "ok" for row in rows)
    print(f"measured={len(rows)} errors={errors} output={args.output}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
