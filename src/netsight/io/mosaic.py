"""GeoTIFF side-scan / backscatter mosaic reader (vendor-neutral fallback input)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import rasterio
from rasterio.enums import MaskFlags
from scipy import ndimage

from netsight.core.hashing import file_sha256
from netsight.core.records import Provenance

NOTE_GAIN = (
    "mosaic input: unknown gain/TVG history and no per-ping geometry; "
    "calibration on mosaics gets a lower claim level"
)

_SENTINEL_MAX = {"uint8": 255, "uint16": 65535}


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


def _infer_nodata_mask(raw: np.ndarray, dtype: str) -> tuple[np.ndarray, int] | None:
    """Find a no-coverage sentinel in an integer raster that declares no nodata.

    Candidates are 0 and the dtype maximum. A candidate qualifies only if it is the
    value of the majority of border pixels; the mask is then the pixels with that
    value that are 4-connected to the border (interior look-alikes stay valid).
    Returns (mask, sentinel) or None.
    """
    if dtype not in _SENTINEL_MAX or raw.size == 0:
        return None
    border = np.concatenate([raw[0], raw[-1], raw[1:-1, 0], raw[1:-1, -1]])
    for candidate in (0, _SENTINEL_MAX[dtype]):
        if (border == candidate).mean() > 0.5:
            labels, n = ndimage.label(raw == candidate)  # default structure: 4-connectivity
            border_labels = np.unique(
                np.concatenate([labels[0], labels[-1], labels[1:-1, 0], labels[1:-1, -1]])
            )
            lut = np.zeros(n + 1, dtype=bool)
            lut[border_labels] = True
            lut[0] = False
            return lut[labels], candidate
    return None


def read_mosaic(path: str | Path, band: int = 1, nodata: float | None = None) -> Mosaic:
    p = Path(path)
    notes = [NOTE_GAIN]
    with rasterio.open(p) as src:
        band_count = src.count
        dtype = src.dtypes[band - 1]
        declared = src.nodata
        array = src.read(band, out_dtype="float32")
        flags = set(src.mask_flag_enums[band - 1])
        has_mask = bool(flags - {MaskFlags.all_valid, MaskFlags.nodata})
        sources = []
        if nodata is not None:
            array[array == np.float32(nodata)] = np.nan
            sources.append("override")
        elif declared is not None:
            array[array == np.float32(declared)] = np.nan
            sources.append("declared")
        if has_mask:
            array[src.read_masks(band) == 0] = np.nan
            sources.append("mask")
            notes.append("dataset mask band (internal mask or alpha) applied as no-coverage")
        if not sources:
            inferred = _infer_nodata_mask(src.read(band), dtype)
            if inferred is None:
                sources.append("none")
                notes.append(
                    "nodata undeclared; no sentinel inferred - all pixels treated as valid"
                )
            else:
                mask, sentinel = inferred
                array[mask] = np.nan
                sources.append("inferred")
                notes.append(
                    f"nodata undeclared; inferred {sentinel} from border-connected "
                    f"no-coverage regions ({int(mask.sum())} pixels)"
                )
        source = "+".join(sources)
        transform = tuple(src.transform)[:6]
        crs = src.crs
        units = "degree" if crs is not None and crs.is_geographic else "metre"
        pixel_size = (abs(float(src.res[0])), abs(float(src.res[1])))
        crs_wkt = crs.to_wkt() if crs is not None else None
    if crs_wkt is None:
        notes.append("mosaic has no CRS")
    if band_count > 1:
        notes.append(f"mosaic has {band_count} bands; only band {band} was read")
    provenance = Provenance(
        str(p), file_sha256(p), "netsight.io.mosaic", f"rasterio {rasterio.__version__}", notes
    )
    extra = {"band": band, "band_count": band_count, "nodata_source": source}
    return Mosaic(array, transform, crs_wkt, pixel_size, units, provenance, extra=extra)
