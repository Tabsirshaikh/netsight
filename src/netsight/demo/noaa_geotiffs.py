"""Cut small georeferenced GeoTIFFs around NOAA-confirmed objects for the map demo and the
WP8 position check.

Each crop keeps the mosaic's CRS and transform, so the dashboard gives its contacts real map
positions. The NOAA position of the object is the crop centre (by construction of the chips),
written to ``truth.json`` for comparing detected positions with NOAA's.

    python -m netsight.demo.noaa_geotiffs --out processed/noaa_geotiffs
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import numpy as np

CROP_PX = 768


def _source(provenance: str) -> Path:
    m = re.search(r"source_path='([^']+)'", provenance)
    if not m:
        raise ValueError("no source path in provenance")
    return Path(m.group(1).replace("\\\\", "\\"))


def crop_all(chips_root: Path, out: Path, crop_px: int = CROP_PX) -> list[dict]:
    import rasterio
    from pyproj import Transformer
    from rasterio.windows import Window

    out.mkdir(parents=True, exist_ok=True)
    truth = []
    for manifest in sorted(chips_root.glob("*/manifest.json")):
        for r in json.loads(manifest.read_text(encoding="utf-8")):
            if r["status"] != "ok" or not r["is_real"]:
                continue
            src = _source(r["provenance"])
            cx = r["window"][0] + r["centre_px"][0]
            cy = r["window"][1] + r["centre_px"][1]
            col0, row0 = int(round(cx - crop_px / 2)), int(round(cy - crop_px / 2))
            with rasterio.open(src) as ds:
                if col0 < 0 or row0 < 0 or col0 + crop_px > ds.width or row0 + crop_px > ds.height:
                    continue
                win = Window(col0, row0, crop_px, crop_px)
                a = ds.read(1, window=win).astype(np.float64)
                nodata = ds.nodata if ds.nodata is not None else 255
                valid = a != nodata
                if valid.mean() < 0.8:
                    continue
                lo, hi = np.percentile(a[valid], [1, 99])
                img = np.clip((a - lo) / max(hi - lo, 1e-9) * 254, 0, 254).astype(np.uint8)
                img[~valid] = 0
                transform = ds.window_transform(win)
                crs = ds.crs
                name = f"{r['survey_id']}_{re.sub(r'[^A-Za-z0-9-]', '_', r['contact_id'])}.tif"
                with rasterio.open(
                    out / name,
                    "w",
                    driver="GTiff",
                    height=crop_px,
                    width=crop_px,
                    count=1,
                    dtype="uint8",
                    crs=crs,
                    transform=transform,
                    compress="LZW",
                ) as dst:
                    dst.write(img, 1)
                x, y = ds.xy(cy, cx, offset="ul")
                lon, lat = Transformer.from_crs(crs, "EPSG:4326", always_xy=True).transform(x, y)
            truth.append(
                {
                    "file": name,
                    "survey_id": r["survey_id"],
                    "contact_id": r["contact_id"],
                    "noaa_lon": lon,
                    "noaa_lat": lat,
                    "noaa_px": [cx - col0, cy - row0],
                }
            )
    (out / "truth.json").write_text(json.dumps(truth, indent=2), encoding="utf-8")
    return truth


def main(argv: list[str] | None = None) -> int:
    from netsight.config import data_dir

    p = argparse.ArgumentParser()
    p.add_argument("--chips", default="processed/noaa_chips")
    p.add_argument("--out", default="processed/noaa_geotiffs")
    a = p.parse_args(argv)
    truth = crop_all(data_dir() / a.chips, data_dir() / a.out)
    print(f"{len(truth)} crops written to {data_dir() / a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
