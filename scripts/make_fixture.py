#!/usr/bin/env python3
"""Create the non-biological deterministic image used for regression testing."""

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw


HERE = Path(__file__).resolve().parent
OUTPUT = HERE.parent / "examples" / "synthetic_histology_fixture.png"


def main() -> None:
    width = height = 512
    y, x = np.mgrid[0:height, 0:width]
    background = np.empty((height, width, 3), dtype=np.float64)
    background[:, :, 0] = 239 + 7 * np.sin(x / 43) + 4 * np.cos(y / 29)
    background[:, :, 1] = 215 + 5 * np.sin((x + y) / 51)
    background[:, :, 2] = 225 + 8 * np.cos((x - y) / 61)
    image = Image.fromarray(np.clip(background, 0, 255).astype(np.uint8), "RGB")
    draw = ImageDraw.Draw(image, "RGBA")

    # Gland-like rings and lumen spaces.
    for cx, cy, rx, ry in [(112, 130, 66, 48), (335, 118, 82, 55), (178, 350, 74, 62), (392, 357, 62, 78)]:
        draw.ellipse((cx-rx, cy-ry, cx+rx, cy+ry), fill=(187, 105, 158, 95), outline=(88, 39, 112, 220), width=9)
        draw.ellipse((cx-rx+18, cy-ry+15, cx+rx-18, cy+ry-15), fill=(250, 241, 244, 240), outline=(126, 67, 139, 180), width=4)

    # Eosin-like oriented stromal bands.
    for offset in range(-180, 420, 22):
        draw.line((0, offset, width, offset + 250), fill=(211, 121, 160, 75), width=7)

    # Fixed-seed nucleus-like objects with spatially varying orientation.
    rng = np.random.default_rng(20260903)
    for index in range(190):
        cx = int(rng.integers(18, width - 18))
        cy = int(rng.integers(18, height - 18))
        rx = int(rng.integers(3, 9))
        ry = int(rng.integers(5, 14))
        alpha = int(rng.integers(150, 240))
        color = (70 + index % 22, 28 + index % 17, 103 + index % 31, alpha)
        draw.ellipse((cx-rx, cy-ry, cx+rx, cy+ry), fill=color)

    # A pale edge and a dark compact island exercise frame and scale responses.
    draw.rectangle((0, 0, 42, height), fill=(250, 247, 246, 220))
    draw.polygon([(425, 18), (502, 42), (478, 126), (414, 96)], fill=(75, 25, 96, 205))
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    image.save(OUTPUT, format="PNG", optimize=False)
    print(OUTPUT)


if __name__ == "__main__":
    main()
