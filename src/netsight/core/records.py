"""Sensor-neutral records shared by every NetSight reader.

Conventions:
- Channel arrays run near -> far: index 0 is the sample nearest the sonar.
- Missing scalar values are NaN, never 0.
- Every position carries its source; a missing position is NaN with NavSource.MISSING.
"""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import asdict, dataclass, field
from enum import StrEnum

import numpy as np


class SensorType(StrEnum):
    SIDESCAN = "sidescan"
    SAS = "sas"
    MBES_BACKSCATTER = "mbes_backscatter"
    FORWARD_LOOKING = "forward_looking"
    MOSAIC = "mosaic"


class NavSource(StrEnum):
    SENSOR = "sensor"  # sensor/towfish position recorded by the acquisition system
    SHIP_LAYBACK = "ship_layback"  # vessel position moved back along heading by recorded layback
    SHIP = "ship"  # vessel position only; towfish offset unknown
    MISSING = "missing"  # no usable position: position withdrawn


class CoordKind(StrEnum):
    LATLON = "latlon"  # x = longitude, y = latitude, degrees
    PROJECTED = "projected"  # x = easting, y = northing, metres
    NONE = "none"


@dataclass(frozen=True)
class SensorDescriptor:
    sensor_type: SensorType
    source_format: str
    model: str | None = None
    frequency_khz: float | None = None
    n_channels: int = 2
    along_track_beamwidth_deg: float | None = None
    across_track_beamwidth_deg: float | None = None

    def to_dict(self) -> dict:
        d = asdict(self)
        d["sensor_type"] = str(self.sensor_type)
        return d


@dataclass
class Ping:
    index: int
    ping_number: int
    time: np.datetime64
    x: float
    y: float
    coord_kind: CoordKind
    nav_source: NavSource
    heading_deg: float
    pitch_deg: float
    roll_deg: float
    altitude_m: float
    slant_range_m: float
    port: np.ndarray
    stbd: np.ndarray
    sound_velocity_ms: float = 1500.0

    def __post_init__(self) -> None:
        self.port = np.asarray(self.port, dtype=np.float32).ravel()
        self.stbd = np.asarray(self.stbd, dtype=np.float32).ravel()
        if self.port.size == 0 or self.port.size != self.stbd.size:
            raise ValueError(
                f"port and starboard need equal, non-zero sample counts "
                f"(got {self.port.size} and {self.stbd.size})"
            )
        if not (math.isfinite(self.slant_range_m) and self.slant_range_m > 0):
            raise ValueError(f"slant_range_m must be positive, got {self.slant_range_m}")

    @property
    def n_samples(self) -> int:
        return int(self.port.size)

    @property
    def sample_spacing_m(self) -> float:
        return self.slant_range_m / self.n_samples


@dataclass
class Provenance:
    source_path: str
    sha256: str
    reader: str
    reader_version: str
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class SonarRecord:
    sensor: SensorDescriptor
    pings: list[Ping]
    provenance: Provenance

    @property
    def n_pings(self) -> int:
        return len(self.pings)

    def channel_matrix(self, side: str) -> np.ndarray:
        """Stack one side's samples as (n_pings, n_samples), in ping order."""
        if side not in ("port", "stbd"):
            raise ValueError(f"side must be 'port' or 'stbd', got {side!r}")
        if not self.pings:
            return np.empty((0, 0), dtype=np.float32)
        counts = {p.n_samples for p in self.pings}
        if len(counts) != 1:
            raise ValueError(f"pings have different sample counts {sorted(counts)}; resample first")
        return np.stack([getattr(p, side) for p in self.pings])

    def nav_source_counts(self) -> dict[str, int]:
        return dict(Counter(str(p.nav_source) for p in self.pings))
