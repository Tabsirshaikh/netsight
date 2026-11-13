"""Map positions and export files for dashboard surveys.

Only georeferenced uploads (GeoTIFF mosaics with a CRS) get map positions. Waterfall images and
plain pictures have no georeference: their contacts are written with the position withdrawn,
never guessed. Mosaic positions carry an assumed georeference error (stated in every record).
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from netsight.export.plan import verification_plan
from netsight.export.vector import contacts_geojson, write_csv, write_geojson, write_kml

CHI2_95_2DOF = 5.991464547107979
MOSAIC_GEOREF_SIGMA_M = 2.0  # assumed 1-sigma error of a mosaic's georeference
METHOD = "mosaic pixel -> CRS via GeoTIFF transform; isotropic error, assumed"


@dataclass(frozen=True)
class Georef:
    transform: tuple[float, float, float, float, float, float]  # affine a, b, c, d, e, f
    crs_wkt: str
    pixel_m: float  # mean pixel size in CRS units (metres for projected CRS)
    projected: bool

    def to_map(self, col: float, row: float) -> tuple[float, float]:
        a, b, c, d, e, f = self.transform
        return a * col + b * row + c, d * col + e * row + f


def georeference(data: bytes, name: str) -> Georef | None:
    """Georeference of a TIFF upload, or None when it has no CRS or an identity transform."""
    if Path(name).suffix.lower() not in {".tif", ".tiff"}:
        return None
    import rasterio
    from rasterio.io import MemoryFile

    try:
        with MemoryFile(data) as memfile, memfile.open() as ds:
            if ds.crs is None or ds.transform.is_identity:
                return None
            t = ds.transform
            return Georef(
                transform=(t.a, t.b, t.c, t.d, t.e, t.f),
                crs_wkt=ds.crs.to_wkt(),
                pixel_m=float((abs(t.a) + abs(t.e)) / 2),
                projected=bool(ds.crs.is_projected),
            )
    except (rasterio.errors.RasterioError, ValueError):
        return None


def contact_position(georef: Georef, box: tuple[float, float, float, float]) -> dict[str, Any]:
    """WGS84 position and 95% ellipse for a box on a georeferenced mosaic."""
    from pyproj import CRS, Transformer

    col, row = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
    x, y = georef.to_map(col, row)
    to_wgs = Transformer.from_crs(CRS.from_wkt(georef.crs_wkt), "EPSG:4326", always_xy=True)
    lon, lat = to_wgs.transform(x, y)
    if georef.projected:
        pixel_sigma = georef.pixel_m / math.sqrt(12)  # uniform quantisation of the box centre
        sigma = math.sqrt(MOSAIC_GEOREF_SIGMA_M**2 + pixel_sigma**2)
        semi = sigma * math.sqrt(CHI2_95_2DOF)
        ellipse: list[float] | None = [semi, semi, 0.0]
        cov = [sigma**2, sigma**2, 0.0]
    else:  # geographic CRS: pixel size is in degrees, no metric ellipse claimed
        ellipse, cov = None, None
    return {
        "lon": float(lon),
        "lat": float(lat),
        "map_x": float(x),
        "map_y": float(y),
        "ellipse95": ellipse,
        "cov_en_m2": cov,
        "method": METHOD,
        "assumed_georef_sigma_m": MOSAIC_GEOREF_SIGMA_M,
    }


def export_records(contacts: list[dict[str, Any]], survey_id: str, claim_level: str) -> list[dict]:
    """Dashboard contacts -> the ContactDict records the export package expects."""
    records = []
    for c in contacts:
        pos = c.get("position") or {}
        records.append(
            {
                "contact_id": c["contact_id"],
                "survey_id": survey_id,
                "lon": pos.get("lon"),
                "lat": pos.get("lat"),
                "ellipse95": pos.get("ellipse95"),
                "p_real": float(c["probability"]),
                "p_real_interval": None,
                "class_probs": {"object": float(c["probability"])},
                "claim_level": claim_level,
                "flagged": True,
                "raw_score": float(c["raw_score"]),
                "evidence": c.get("evidence") or {},
                "image": c["image"],
                "box_px": [float(v) for v in c["box"]],
            }
        )
    return records


def write_exports(out_dir: Path, records: list[dict], *, banner: str, name: str) -> dict[str, str]:
    """Write GeoJSON, KML, CSV and the verification plan; return file names by format."""
    files = {
        "geojson": "contacts.geojson",
        "kml": "contacts.kml",
        "csv": "contacts.csv",
        "plan": "verification_plan.json",
    }
    write_geojson(
        out_dir / files["geojson"], contacts_geojson(records, research_banner=banner, ellipses=True)
    )
    write_kml(out_dir / files["kml"], records, name=name, research_banner=banner)
    write_csv(out_dir / files["csv"], records)
    plan = verification_plan(records)
    (out_dir / files["plan"]).write_text(json.dumps(plan, indent=2, default=str), "utf-8")
    return files


def write_completeness_tiff(
    path: Path,
    cells: list[dict],
    georef: Georef,
    shape: tuple[int, int],
    grid: tuple[int, int],
    *,
    banner: str,
) -> Path:
    """Pd lower bound per cell as a GeoTIFF on the mosaic's own grid (cells without enough
    trials are nodata)."""
    import rasterio
    from rasterio.transform import Affine

    rows, cols = grid
    h, w = shape
    arr = np.full((rows, cols), -1.0, np.float32)
    for c in cells:
        if c["status"] == "ok":
            arr[c["row"], c["col"]] = c["pd_lower"]
    t = Affine(*georef.transform) * Affine.scale(w / cols, h / rows)
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=rows,
        width=cols,
        count=1,
        dtype="float32",
        crs=rasterio.crs.CRS.from_wkt(georef.crs_wkt),
        transform=t,
        nodata=-1.0,
        compress="LZW",
    ) as ds:
        ds.write(arr, 1)
        ds.set_band_description(1, "Pd lower bound (90%), injected reference targets")
        ds.update_tags(NETSIGHT_BANNER=banner)
    return path


def write_multipass_tiff(
    path: Path,
    passes: list[dict],
    *,
    banner: str,
    cell_m: float | None = None,
    max_cells: int = 4_000_000,
) -> dict:
    """Multi-pass Pd interval on a common map grid (plan 16 item 6).

    Each pass: {georef, shape, grid, cells (completeness cells), not_searched (mask), optional
    pd_lower_pass (lower bound from all the pass's trials)}. Per map cell and pass, Pd = the
    pass's cell lower bound there (pd_lower_pass where the cell lacks trials), 0 where that pass
    searched nothing, no value outside its footprint. Bands: 1 = max over
    passes (misses repeat), 2 = 1 - prod(1 - Pd) (misses independent), 3 = passes with a value.
    """
    import rasterio
    from rasterio.transform import Affine

    from netsight.trust.coverage import multipass_grid

    usable = [p for p in passes if p["georef"] is not None and p["georef"].projected]
    if len(usable) < 2 or len({p["georef"].crs_wkt for p in usable}) != 1:
        return {
            "available": False,
            "reason": "needs at least two georeferenced passes in one projected (metre) CRS",
        }
    corners = []
    for p in usable:
        h, w = p["shape"]
        corners += [p["georef"].to_map(c, r) for c in (0, w) for r in (0, h)]
    xs, ys = [c[0] for c in corners], [c[1] for c in corners]
    if cell_m is None:
        sizes = [
            max(p["shape"][1] / p["grid"][1], p["shape"][0] / p["grid"][0]) * p["georef"].pixel_m
            for p in usable
        ]
        cell_m = float(np.median(sizes)) / 4
    cols = max(1, int(np.ceil((max(xs) - min(xs)) / cell_m - 1e-9)))
    rows = max(1, int(np.ceil((max(ys) - min(ys)) / cell_m - 1e-9)))
    if rows * cols > max_cells:
        scale = np.sqrt(rows * cols / max_cells)
        cell_m *= scale
        cols = max(1, int(np.ceil((max(xs) - min(xs)) / cell_m)))
        rows = max(1, int(np.ceil((max(ys) - min(ys)) / cell_m)))
    grid_t = Affine(cell_m, 0, min(xs), 0, -cell_m, max(ys))
    cx, cy = np.meshgrid(np.arange(cols) + 0.5, np.arange(rows) + 0.5)
    mx, my = grid_t @ (cx, cy)
    layers = []
    for p in usable:
        h, w = p["shape"]
        gr, gc = p["grid"]
        px, py = ~Affine(*p["georef"].transform) @ (mx, my)
        inside = (px >= 0) & (px < w) & (py >= 0) & (py < h)
        col = np.clip(px.astype(int), 0, w - 1)
        row = np.clip(py.astype(int), 0, h - 1)
        # cells without enough trials fall back to the pass's pooled lower bound, if given
        cell_pd = np.full((gr, gc), float(p.get("pd_lower_pass", np.nan)))
        for c in p["cells"]:
            if c["status"] == "ok":
                cell_pd[c["row"], c["col"]] = c["pd_lower"]
        pd = cell_pd[row * gr // h, col * gc // w]
        pd = np.where(np.asarray(p["not_searched"], bool)[row, col], 0.0, pd)
        layers.append(np.where(inside, pd, np.nan))
    lo, hi, n = multipass_grid(layers)
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=rows,
        width=cols,
        count=3,
        dtype="float32",
        crs=rasterio.crs.CRS.from_wkt(usable[0]["georef"].crs_wkt),
        transform=grid_t,
        nodata=-1.0,
        compress="LZW",
    ) as ds:
        ds.write(np.where(np.isfinite(lo), lo, -1).astype(np.float32), 1)
        ds.write(np.where(np.isfinite(hi), hi, -1).astype(np.float32), 2)
        ds.write(n.astype(np.float32), 3)
        ds.set_band_description(1, "Pd lower bound, misses repeat on every pass (max)")
        ds.set_band_description(2, "Pd lower bound, misses independent between passes")
        ds.set_band_description(3, "passes with a Pd value")
        ds.update_tags(NETSIGHT_BANNER=banner)
    overlap = (n >= 2) & np.isfinite(lo)
    return {
        "available": True,
        "passes": len(usable),
        "cell_m": cell_m,
        "overlap_km2": float(overlap.sum() * cell_m * cell_m / 1e6),
        "overlap_pd_max_median": float(np.median(lo[overlap])) if overlap.any() else None,
        "overlap_pd_independent_median": float(np.median(hi[overlap])) if overlap.any() else None,
        "note": (
            "Where passes overlap, the true Pd lies between the two values: the lower assumes a "
            "missed object is missed again on every pass, the upper that misses are independent."
        ),
    }
