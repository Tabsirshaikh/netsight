"""Read the navigation and beam-array subset of GSF v3.x.

Verified on a real NOAA file (CC_BlockA03, Reson 7125; tests/data) as well as synthetic
files. The first version was written from the format description alone and read scale
factors from the wrong subrecord, so it could not read real files.

Checksum words are consumed but not verified. Compressed array encodings other
than uncompressed integer widths are rejected rather than guessed. Scale factors
are file-local and persist between pings. A measured array without a known scale
factor is rejected: interpreting it with an invented scale would be unsafe.
"""

import re
import struct
from collections import Counter

import numpy as np

from netsight.core.hashing import file_sha256
from netsight.core.records import Provenance

from ._multibeam_binary import (
    READER_VERSION,
    SYNTHETIC_NOTICE,
    PathInput,
    coordinate,
    heading,
    read_source,
    require,
    timestamp,
)
from .multibeam import MultibeamPing, MultibeamRecord

# Record identifiers as in gsf.h (GSF_RECORD_*); checked on a real NOAA file (2026-11-13).
_RECORD_NAMES = {
    1: "HEADER",
    2: "SWATH_BATHYMETRY_PING",
    3: "SOUND_VELOCITY_PROFILE",
    4: "PROCESSING_PARAMETERS",
    5: "SENSOR_PARAMETERS",
    6: "COMMENT",
    7: "HISTORY",
    8: "NAVIGATION_ERROR",
    9: "SWATH_BATHY_SUMMARY",
    10: "SINGLE_BEAM_PING",
    11: "HV_NAVIGATION_ERROR",
    12: "ATTITUDE",
}
_SCALE_FACTORS = 100  # GSF_SWATH_BATHY_SUBRECORD_SCALE_FACTORS
_PING_HEADER = struct.Struct(">4i5hiH3h2H3ih")
_ARRAY_IDS = {1, 2, 3, 6, 7}
# Each entry is (compression/width flag, multiplier, offset).
type ScaleFactors = dict[int, tuple[int, int, int]]


def _scales(payload: bytes, scales: ScaleFactors) -> None:
    require(payload, 0, 4, "GSF scale-factor count")
    count = struct.unpack_from(">i", payload)[0]
    if count < 0 or len(payload) != 4 + 12 * count:
        raise ValueError("Invalid GSF scale-factor count or subrecord length")
    for position in range(4, len(payload), 12):
        word, multiplier, offset = struct.unpack_from(">Iii", payload, position)
        identifier = word >> 24
        flag = word & 0xFFFFFF
        # Accept both the task's low-byte representation and the published
        # compressionFlag byte immediately below the subrecord-id byte.
        if flag > 0xFF and flag & 0xFFFF == 0:
            flag >>= 16
        if multiplier <= 0:
            raise ValueError(f"GSF subrecord {identifier}: multiplier must be positive")
        scales[identifier] = (flag, multiplier, offset)


def _array(payload: bytes, identifier: int, beams: int, scales: ScaleFactors) -> np.ndarray:
    if identifier not in scales:
        raise ValueError(f"GSF subrecord {identifier}: no scale factor is available")
    flag, multiplier, offset = scales[identifier]
    if flag & ~0x30 or flag & 0x30 == 0x30:
        raise ValueError(f"GSF subrecord {identifier}: unsupported compression flag {flag:#x}")
    width = {0: 2, 0x10: 1, 0x20: 4}[flag & 0x30]
    if len(payload) != beams * width:
        raise ValueError(f"GSF subrecord {identifier}: array size does not match beam count")
    kind = "u" if identifier == 1 else "i"
    raw = np.frombuffer(payload, dtype=f">{kind}{width}")
    return raw.astype(np.float64) / multiplier - offset


def _ping(
    payload: bytes,
    scales: ScaleFactors,
    skipped: Counter[str],
    amplitude_sources: Counter[str],
    sensors: set[int],
) -> MultibeamPing:
    require(payload, 0, _PING_HEADER.size, "GSF ping header")
    header = _PING_HEADER.unpack_from(payload)
    seconds, nanoseconds, longitude, latitude, beams = header[:5]
    if beams < 0:
        raise ValueError("GSF ping has a negative beam count")

    subrecords: dict[int, bytes] = {}
    position = _PING_HEADER.size
    while position < len(payload):
        require(payload, position, 4, "GSF subrecord header")
        word = struct.unpack_from(">I", payload, position)[0]
        identifier, size = word >> 24, word & 0xFFFFFF
        position += 4
        require(payload, position, size, f"GSF subrecord {identifier}")
        body = payload[position : position + size]
        position += size
        if identifier == 0 and size == 0:
            continue  # zero-length end marker written by some vendors
        if identifier in _ARRAY_IDS | {16, _SCALE_FACTORS}:
            if identifier in subrecords:
                raise ValueError(f"Duplicate GSF subrecord {identifier} in one ping")
            subrecords[identifier] = body
        else:
            skipped[f"subrecord:{identifier}"] += 1
            if identifier > _SCALE_FACTORS:
                sensors.add(identifier)

    if _SCALE_FACTORS in subrecords:
        _scales(subrecords[_SCALE_FACTORS], scales)
    arrays = {
        identifier: _array(body, identifier, beams, scales)
        for identifier, body in subrecords.items()
        if identifier in _ARRAY_IDS
    }

    def values(identifier: int) -> np.ndarray:
        return arrays.get(identifier, np.full(beams, np.nan, dtype=np.float64))

    flags = None
    valid = np.ones(beams, dtype=np.bool_)
    if 16 in subrecords:
        if len(subrecords[16]) != beams:
            raise ValueError("GSF BEAM_FLAGS size does not match beam count")
        flags = np.frombuffer(subrecords[16], dtype=np.uint8)
        valid = flags == 0
    amplitude_id = 6 if 6 in arrays else 7
    if amplitude_id in arrays:
        amplitude_sources["MEAN_CAL_AMPLITUDE" if amplitude_id == 6 else "MEAN_REL_AMPLITUDE"] += 1

    return MultibeamPing(
        time=timestamp(seconds, nanoseconds, "GSF ping"),
        latitude=coordinate(latitude / 10_000_000, 90),
        longitude=coordinate(longitude / 10_000_000, 180),
        heading=heading(header[10] / 100),
        sound_speed=float("nan"),
        across_track=values(2),
        along_track=values(3),
        depth=values(1),
        backscatter=values(amplitude_id),
        valid=valid,
        beam_flags=flags,
    )


def read_gsf(path: PathInput) -> MultibeamRecord:
    """Read the supported GSF v3.x subset with counted skips and provenance.

    Verified on a real NOAA file (tests/test_gsf_real.py) and on synthetic files.

    Sensor-specific payloads, including sensor-specific sound speeds, are not
    decoded. Their IDs are retained as model identifiers and counted as skips.
    """
    source, data = read_source(path)
    counts: Counter[str] = Counter()
    skipped: Counter[str] = Counter()
    amplitude_sources: Counter[str] = Counter()
    scales: ScaleFactors = {}
    sensors: set[int] = set()
    pings: list[MultibeamPing] = []
    version: str | None = None
    checksums = 0
    position = 0

    while position < len(data):
        record_offset = position
        require(data, position, 8, "GSF record header")
        size, word = struct.unpack_from(">II", data, position)
        position += 8
        identifier = word & 0x3FFFFF
        name = _RECORD_NAMES.get(identifier, f"UNKNOWN_{identifier}")
        counts[name] += 1
        if word & 0x80000000:
            require(data, position, 4, "GSF checksum")
            position += 4
            checksums += 1
        require(data, position, size, f"GSF {name} at record offset {record_offset}")
        payload = data[position : position + size]
        position += size
        padding = (-size) % 4
        require(data, position, padding, "GSF record padding")
        position += padding
        if identifier == 1:
            try:
                parsed_version = payload.split(b"\0", 1)[0].decode("ascii").strip()
            except UnicodeDecodeError as exc:
                raise ValueError("Invalid ASCII in GSF header") from exc
            if not re.fullmatch(r"GSF-v03\.\d+", parsed_version):
                raise ValueError(f"Unsupported GSF version: {parsed_version!r}")
            if version is not None and version != parsed_version:
                raise ValueError("Conflicting GSF version headers")
            version = parsed_version
        elif identifier == 2:
            pings.append(_ping(payload, scales, skipped, amplitude_sources, sensors))
        else:
            skipped[name] += 1

    if version is None:
        raise ValueError("Missing GSF v3.x HEADER record")
    notes = [SYNTHETIC_NOTICE]
    notes.extend(f"Skipped {name}: {count}" for name, count in sorted(skipped.items()))
    notes.extend(
        f"Backscatter source {name}: {count} pings"
        for name, count in sorted(amplitude_sources.items())
    )
    if checksums:
        notes.append(f"Checksum words consumed without verification: {checksums}")
    notes.append("Sensor-specific sound speed is not decoded; missing sound speed is NaN.")
    sonar_model = ", ".join(f"GSF sensor id {value}" for value in sorted(sensors)) or None
    return MultibeamRecord(
        source_format="GSF",
        sonar_model=sonar_model,
        pings=pings,
        provenance=Provenance(
            source_path=str(source),
            sha256=file_sha256(source),
            reader="netsight.io.gsf.read_gsf",
            reader_version=READER_VERSION,
            notes=list(notes),
        ),
        record_counts=dict(counts),
        notes=notes,
        version=version,
        skipped_record_types=dict(skipped),
    )
