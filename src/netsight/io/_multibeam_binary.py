"""Small checked binary-reading utilities shared by the multibeam readers."""

from os import PathLike
from pathlib import Path

import numpy as np

PathInput = str | PathLike[str]

READER_VERSION = "1.0"
SYNTHETIC_NOTICE = (
    "Tested on synthetic files written from the published format description; "
    "not yet verified on vendor files."
)


def read_source(path: PathInput) -> tuple[Path, bytes]:
    """Read a source, translating invalid paths and I/O failures to ValueError."""
    try:
        source = Path(path)
        return source, source.read_bytes()
    except (OSError, TypeError, ValueError) as exc:
        raise ValueError(f"Cannot read multibeam source {path!r}: {exc}") from exc


def require(data: bytes, offset: int, size: int, context: str) -> None:
    """Check a byte range before unpacking it."""
    if offset < 0 or size < 0 or offset > len(data) or size > len(data) - offset:
        raise ValueError(f"Truncated {context} at offset {offset}: need {size} bytes")


def timestamp(seconds: int, nanoseconds: int, context: str) -> np.datetime64:
    """Construct a UTC timestamp using integer arithmetic without float rounding."""
    if not 0 <= nanoseconds < 1_000_000_000:
        raise ValueError(f"Invalid nanoseconds in {context}: {nanoseconds}")
    value = seconds * 1_000_000_000 + nanoseconds
    if not -(2**63) < value < 2**63:
        raise ValueError(f"Timestamp outside datetime64[ns] range in {context}")
    return np.datetime64(value, "ns")


def coordinate(value: float, limit: float) -> float:
    """Retain only finite coordinates within their physical range."""
    return float(value) if np.isfinite(value) and abs(value) <= limit else float("nan")


def heading(value: float) -> float:
    """Retain valid headings without wrapping missing-value sentinels."""
    return float(value) if np.isfinite(value) and 0 <= value <= 360 else float("nan")
