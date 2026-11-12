"""Run the dashboard analysis on the NOAA GeoTIFF crops and compare contact positions with
NOAA's recorded positions (WP8 check on known targets).

    python -m netsight.demo.noaa_geo_check --crops processed/noaa_geotiffs --out runs/noaa_geo_v0.4
"""

from __future__ import annotations

import argparse
import json
import math
import shutil

import numpy as np


def main(argv: list[str] | None = None) -> int:
    from netsight.app.server import analyze_sync, decode_image, default_runtime_factory
    from netsight.config import data_dir

    p = argparse.ArgumentParser()
    p.add_argument("--crops", default="processed/noaa_geotiffs")
    p.add_argument("--out", default="runs/noaa_geo_v0.4")
    p.add_argument("--budget", type=float, default=1.0)
    a = p.parse_args(argv)
    root = data_dir()
    crops = root / a.crops
    truth = {t["file"]: t for t in json.loads((crops / "truth.json").read_text("utf-8"))}
    images = []
    for name in sorted(truth):
        data = (crops / name).read_bytes()
        images.append((name, decode_image(data, name), data))
    runtime = default_runtime_factory()
    result = analyze_sync(runtime, images, "general", "general", a.budget, True, completeness=True)
    out = root / a.out
    out.mkdir(parents=True, exist_ok=True)
    pack = runtime.output_dir / result["survey_id"]
    for f in pack.iterdir():
        if f.is_file():
            shutil.copy2(f, out / f.name)
    rows = []
    for img in result["images"]:
        t = truth[img["name"]]
        flagged = [d for d in img["detections"] if d["flagged"]]
        best = None
        for d in flagged:
            pos = result["positions"].get(d["id"])
            if not pos:
                continue
            dn = (pos["lat"] - t["noaa_lat"]) * 111320
            de = (pos["lon"] - t["noaa_lon"]) * 111320 * math.cos(math.radians(t["noaa_lat"]))
            dist = math.hypot(de, dn)
            if best is None or dist < best["distance_m"]:
                semi = pos["ellipse95"][0] if pos["ellipse95"] else float("nan")
                best = {
                    "contact": d["id"],
                    "distance_m": dist,
                    "ellipse95_m": semi,
                    "inside_ellipse": dist <= semi,
                    "p_real": d["probability"],
                }
        rows.append(
            {
                "file": img["name"],
                "flagged": len(flagged),
                "nearest": best,
                "found_within_25m": bool(best and best["distance_m"] <= 25),
            }
        )
    found = [r for r in rows if r["found_within_25m"]]
    summary = {
        "survey_id": result["survey_id"],
        "claim": result["claim"],
        "images": len(rows),
        "noaa_objects_found_within_25m": len(found),
        "median_distance_m_found": float(np.median([r["nearest"]["distance_m"] for r in found]))
        if found
        else None,
        "inside_95_ellipse": sum(r["nearest"]["inside_ellipse"] for r in found),
        "completeness_pd": (result.get("completeness") or {}).get("pd"),
        "completeness_pd_lower90": (result.get("completeness") or {}).get("pd_lower90"),
        "rows": rows,
    }
    (out / "geo_check.json").write_text(json.dumps(summary, indent=2, default=str), "utf-8")
    print(json.dumps({k: v for k, v in summary.items() if k != "rows"}, indent=2, default=str))
    for r in rows:
        print(r)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
