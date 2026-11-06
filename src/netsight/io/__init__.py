"""Format adapters (layer L0): every reader returns NetSight's own records."""

from __future__ import annotations

from pathlib import Path

from netsight.core.records import SonarRecord
from netsight.io.jsf import read_jsf
from netsight.io.mosaic import Mosaic, read_mosaic
from netsight.io.xtf import read_xtf


class UnsupportedFormatError(ValueError):
    pass


def open_survey(path: str | Path) -> SonarRecord | Mosaic:
    suffix = Path(path).suffix.lower()
    if suffix == ".xtf":
        return read_xtf(path)
    if suffix == ".jsf":
        return read_jsf(path)
    if suffix in (".tif", ".tiff"):
        return read_mosaic(path)
    raise UnsupportedFormatError(
        f"unsupported survey format {suffix!r} (supported: .xtf .jsf .tif .tiff)"
    )
