"""Format-independent multibeam data, with sensor navigation and explicit missing values."""

from dataclasses import dataclass, field

import numpy as np
from numpy.typing import NDArray

from netsight.core.records import Provenance


@dataclass(frozen=True)
class MultibeamPing:
    """One ping; time is UTC and distances are relative to the format's reference point.

    Across-track is starboard-positive and depth is positive down. Readers do not
    synthesize navigation, apply lever arms, or apply tide/depth corrections.
    Missing numeric measurements are NaN. Validity describes the recorded beam
    classification, not whether every measurement is available.
    """

    time: np.datetime64
    latitude: float
    longitude: float
    heading: float
    sound_speed: float
    across_track: NDArray[np.float64]
    along_track: NDArray[np.float64]
    depth: NDArray[np.float64]
    backscatter: NDArray[np.float64]
    valid: NDArray[np.bool_]
    beam_flags: NDArray[np.uint8] | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.time, np.datetime64):
            raise ValueError("time must be a numpy datetime64")
        object.__setattr__(self, "time", self.time.astype("datetime64[ns]"))
        size: int | None = None
        for name in ("across_track", "along_track", "depth", "backscatter", "valid"):
            dtype = np.bool_ if name == "valid" else np.float64
            array = np.array(getattr(self, name), dtype=dtype, copy=True)
            if array.ndim != 1:
                raise ValueError(f"{name} must be a one-dimensional array")
            if size is None:
                size = len(array)
            elif len(array) != size:
                raise ValueError("all per-beam arrays must have the same length")
            array.setflags(write=False)
            object.__setattr__(self, name, array)
        if self.beam_flags is not None:
            flags = np.array(self.beam_flags, dtype=np.uint8, copy=True)
            if flags.ndim != 1 or len(flags) != size:
                raise ValueError("beam_flags must match the other per-beam arrays")
            flags.setflags(write=False)
            object.__setattr__(self, "beam_flags", flags)


@dataclass(frozen=True)
class MultibeamRecord:
    """Decoded pings and file provenance.

    ``version`` preserves the GSF header or describes KMALL datagram versions;
    KMALL's datagram version byte is not a specification revision letter.
    ``skipped_record_types`` includes counted, unparsed GSF subrecord types.
    """

    source_format: str
    sonar_model: str | None
    pings: list[MultibeamPing]
    provenance: Provenance
    record_counts: dict[str, int]
    notes: list[str]
    version: str | None = None
    skipped_record_types: dict[str, int] = field(default_factory=dict)

    @property
    def number_of_pings(self) -> int:
        """Return the number of decoded pings."""
        return len(self.pings)

    @property
    def nav_source(self) -> str:
        """Return 'sensor' only when every ping has finite sensor lat/lon."""
        if not self.pings:
            return "missing"
        return (
            "sensor"
            if all(np.isfinite(p.latitude) and np.isfinite(p.longitude) for p in self.pings)
            else "missing"
        )

    def backscatter_matrix(self) -> NDArray[np.float64]:
        """Return ping-major backscatter, padding shorter pings with NaN."""
        width = max((len(p.backscatter) for p in self.pings), default=0)
        result = np.full((len(self.pings), width), np.nan, dtype=np.float64)
        for row, ping in enumerate(self.pings):
            result[row, : len(ping.backscatter)] = ping.backscatter
        return result
