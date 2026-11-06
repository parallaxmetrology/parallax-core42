"""Re-measure the TCGA-COAD route example from the public tile archive.

Tiles: Kather et al. 2020, TCGA tile archive on Zenodo (record 3784345), one zip per
diagnostic slide named like `TCGA-AA-3488-01Z-00-DX1.<uuid>.zip`, 512-px tumour tiles.

    python measure_tcga_tiles.py --tiles /path/to/tcga_tiles --routes routes.csv --out tile_measurements

Selection (fixed in PLAN.md): per patient, tiles in sorted name order are visited in
the order of numpy default_rng(20261106).permutation; tiles with mean RGB >= 220 are
skipped; the first 8 are kept. Two arms: raw RGB and the bundled fixed-Macenko target.
"""
from __future__ import annotations

import argparse
import io
import zipfile
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image

import parallax_core42 as pc

TARGET = Path(__file__).resolve().parents[2] / "references" / "tcga_fixed_macenko_target.json"


def pick(zip_path: Path, n: int = 8) -> list[str]:
    z = zipfile.ZipFile(zip_path)
    names = sorted(x for x in z.namelist() if x.lower().endswith((".jpg", ".jpeg")) and not x.startswith("__MACOSX"))
    rng = np.random.default_rng(20261106)
    got = []
    for i in rng.permutation(len(names)):
        if np.asarray(Image.open(io.BytesIO(z.read(names[i]))).convert("RGB")).mean() >= 220:
            continue
        got.append(names[i])
        if len(got) == n:
            break
    return got


def work(job: tuple[str, str, str, str]) -> list[dict]:
    route, patient, zip_path, name = job
    rgb = np.asarray(Image.open(io.BytesIO(zipfile.ZipFile(zip_path).read(name))).convert("RGB"))
    norm = pc.load_target(TARGET)
    rows = []
    for arm, img in (("raw", rgb), ("macenko", None)):
        try:
            r = pc.measure_rgb(img if img is not None else norm.transform(rgb), source_id=name)
        except Exception as e:  # noqa: BLE001 - record and continue
            r = {"status": f"error: {e}"}
        rows.append({"arm": arm, "route": route, "patient": patient, "member": name.split("/")[-1],
                     **{k: r.get(k) for k in ("status", *pc.AXES)}})
    return rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tiles", required=True, type=Path, help="folder of per-slide tile zips")
    ap.add_argument("--routes", required=True, type=Path, help="CSV with columns patient,route")
    ap.add_argument("--out", default="tile_measurements")
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args()
    routes = pd.read_csv(a.routes)
    jobs = []
    for patient, route in routes[["patient", "route"]].itertuples(index=False):
        zips = sorted(a.tiles.glob(f"{patient}*.zip"))
        if zips:
            jobs += [(route, patient, str(zips[0]), name) for name in pick(zips[0])]
    with ProcessPoolExecutor(a.workers) as ex:
        rows = [r for rr in ex.map(work, jobs, chunksize=4) for r in rr]
    df = pd.DataFrame(rows)
    for arm, g in df.groupby("arm"):
        g.drop(columns="arm").to_csv(f"{a.out}_{arm}.csv", index=False)
    print(df.groupby(["arm", "status"]).size())


if __name__ == "__main__":
    main()
