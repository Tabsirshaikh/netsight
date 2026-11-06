"""GeoTIFF side-scan / backscatter mosaic reader (vendor-neutral fallback input)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import rasterio

from netsight.core.hashing import file_sha256
from netsight.core.records import Provenance

NOTE_GAIN = (
    "mosaic input: unknown gain/TVG history and no per-ping geometry; "
    "calibration on mosaics gets a lower claim level"
)


@dataclass
class Mosaic:
    array: np.ndarray
    transform: tuple[float, float, float, float, float, float]
    crs_wkt: str | None
    pixel_size: tuple[float, float]
    pixel_units: str
    provenance: Provenance
    gain_history_known: bool = False
    extra: dict = field(default_factory=dict)

    @property
    def valid_fraction(self) -> float:
        return float(np.isfinite(self.array).mean()) if self.array.size else 0.0


def read_mosaic(path: str | Path, band: int = 1) -> Mosaic:
    p = Path(path)
    with rasterio.open(p) as src:
        array = src.read(band, masked=True).astype(np.float32).filled(np.nan)
        transform = tuple(src.transform)[:6]
        crs = src.crs
        units = "degree" if crs is not None and crs.is_geographic else "metre"
        pixel_size = (abs(float(src.res[0])), abs(float(src.res[1])))
        crs_wkt = crs.to_wkt() if crs is not None else None
    notes = [NOTE_GAIN]
    if crs_wkt is None:
        notes.append("mosaic has no CRS")
    provenance = Provenance(
        str(p), file_sha256(p), "netsight.io.mosaic", f"rasterio {rasterio.__version__}", notes
    )
    return Mosaic(array, transform, crs_wkt, pixel_size, units, provenance)
