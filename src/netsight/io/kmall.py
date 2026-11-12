"""Read the navigation and sounding subset of Kongsberg KMALL MRZ datagrams.

Tested on synthetic files written from the published format description;
not yet verified on vendor files.

The offset tables below follow the published EM datagram format Rev. H/I,
including fields not extracted here. In that layout reflectivity1_dB is at byte
48, not 12 (rangeFactor); z_reRefPoint_m is at byte 96, not 72
(beamAngleReRx_deg). Offsets are relative to their respective structures.

Multipart MRZ datagrams and multi-fan pings are explicitly rejected, rather than
returning incomplete or incorrectly assembled pings. Seabed-image samples and
fields not needed for the returned measurements are not decoded.
"""

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

# Kongsberg EM datagram format Rev. H/I: EMdgmMRZ_pingInfo.
PING_INFO_OFFSETS = {
    "numBytesInfoData": 0,
    "numTxSectors": 92,
    "numBytesPerTxSector": 94,
    "headingVessel_deg": 96,
    "soundSpeedAtTxDepth_mPerSec": 100,
    "latitude_deg": 124,
    "longitude_deg": 132,
}

# Kongsberg EM datagram format Rev. H/I: EMdgmMRZ_sounding, 120-byte base.
SOUNDING_OFFSETS = {
    "detectionType": 3,
    "reflectivity1_dB": 48,
    "z_reRefPoint_m": 96,
    "y_reRefPoint_m": 100,
    "x_reRefPoint_m": 104,
    "SIstartRange_samples": 114,
    "SIcentreSample": 116,
    "SInumSamples": 118,
}

_HEADER = struct.Struct("<I4sBBHII")


def _mrz(body: bytes, seconds: int, nanoseconds: int, datagram_offset: int) -> MultibeamPing:
    context = f"KMALL #MRZ at offset {datagram_offset}"
    require(body, 0, 4, f"{context} partition")
    partitions, partition = struct.unpack_from("<HH", body)
    if partitions != 1 or partition != 1:
        raise ValueError(f"{context}: multipart MRZ is not supported")

    position = 4
    require(body, position, 12, f"{context} common part")
    common_size, _, fans, fan_index = struct.unpack_from("<HHBB", body, position)
    if common_size < 12:
        raise ValueError(f"{context}: numBytesCmnPart must be at least 12")
    require(body, position, common_size, f"{context} common part")
    if fans != 1 or fan_index != 0:
        raise ValueError(f"{context}: multi-fan MRZ pings are not supported")
    position += common_size

    require(body, position, 2, f"{context} pingInfo size")
    info_size = struct.unpack_from("<H", body, position)[0]
    if info_size < 140:
        raise ValueError(f"{context}: pingInfo is too short for navigation")
    require(body, position, info_size, f"{context} pingInfo")
    info = body[position : position + info_size]

    def info_value(name: str, fmt: str) -> int | float:
        return struct.unpack_from(f"<{fmt}", info, PING_INFO_OFFSETS[name])[0]

    tx_count = int(info_value("numTxSectors", "H"))
    tx_size = int(info_value("numBytesPerTxSector", "H"))
    if tx_count and not tx_size:
        raise ValueError(f"{context}: zero numBytesPerTxSector with nonempty sectors")
    position += info_size
    require(body, position, tx_count * tx_size, f"{context} transmit sectors")
    position += tx_count * tx_size

    require(body, position, 32, f"{context} rxInfo")
    rx_size, main_count, valid_count, sounding_size = struct.unpack_from("<4H", body, position)
    extra_count, class_count, class_size = struct.unpack_from("<3H", body, position + 26)
    if rx_size < 32:
        raise ValueError(f"{context}: numBytesRxInfo must be at least 32")
    if valid_count > main_count:
        raise ValueError(f"{context}: valid main sounding count exceeds maximum count")
    if sounding_size < 120:
        raise ValueError(f"{context}: numBytesPerSounding must be at least 120")
    if class_count and not class_size:
        raise ValueError(f"{context}: zero extra-detection class size")
    require(body, position, rx_size, f"{context} rxInfo")
    position += rx_size
    require(body, position, class_count * class_size, f"{context} extra-detection classes")
    position += class_count * class_size

    count = main_count + extra_count
    require(body, position, count * sounding_size, f"{context} soundings")
    depth = np.full(count, np.nan, dtype=np.float64)
    across = np.full(count, np.nan, dtype=np.float64)
    along = np.full(count, np.nan, dtype=np.float64)
    backscatter = np.full(count, np.nan, dtype=np.float64)
    flags = np.empty(count, dtype=np.uint8)
    sample_count = 0
    for index in range(count):
        start = position + index * sounding_size
        flags[index] = body[start + SOUNDING_OFFSETS["detectionType"]]
        for destination, field in (
            (depth, "z_reRefPoint_m"),
            (across, "y_reRefPoint_m"),
            (along, "x_reRefPoint_m"),
            (backscatter, "reflectivity1_dB"),
        ):
            destination[index] = struct.unpack_from("<f", body, start + SOUNDING_OFFSETS[field])[0]
        sample_count += struct.unpack_from("<H", body, start + SOUNDING_OFFSETS["SInumSamples"])[0]
    position += count * sounding_size
    require(body, position, sample_count * 2, f"{context} seabed-image samples")

    sound_speed = float(info_value("soundSpeedAtTxDepth_mPerSec", "f"))
    if not np.isfinite(sound_speed) or sound_speed <= 0:
        sound_speed = float("nan")
    return MultibeamPing(
        time=timestamp(seconds, nanoseconds, context),
        latitude=coordinate(float(info_value("latitude_deg", "d")), 90),
        longitude=coordinate(float(info_value("longitude_deg", "d")), 180),
        heading=heading(float(info_value("headingVessel_deg", "f"))),
        sound_speed=sound_speed,
        across_track=across,
        along_track=along,
        depth=depth,
        backscatter=backscatter,
        valid=(flags == 0) | (flags == 1),
        beam_flags=flags,
    )


def read_kmall(path: PathInput) -> MultibeamRecord:
    """Read single-part, single-fan MRZ pings; count all other datagram types.

    Tested on synthetic files written from the published format description;
    not yet verified on vendor files.

    MRZ datagram versions 0 through 3 share the extracted structure prefixes.
    Larger structures are traversed using their declared byte lengths.
    """
    source, data = read_source(path)
    if not data:
        raise ValueError("Empty KMALL file")
    counts: Counter[str] = Counter()
    skipped: Counter[str] = Counter()
    versions: dict[str, set[int]] = {}
    models: set[int] = set()
    pings: list[MultibeamPing] = []
    position = 0
    while position < len(data):
        require(data, position, _HEADER.size, "KMALL datagram header")
        size, type_bytes, version, _, model, seconds, nanoseconds = _HEADER.unpack_from(
            data, position
        )
        if size < _HEADER.size + 4:
            raise ValueError(f"Invalid KMALL datagram length {size} at offset {position}")
        require(data, position, size, f"KMALL datagram at offset {position}")
        repeated_size = struct.unpack_from("<I", data, position + size - 4)[0]
        if repeated_size != size:
            raise ValueError(
                f"KMALL trailing-length mismatch at offset {position}: "
                f"header {size}, trailer {repeated_size}"
            )
        try:
            name = type_bytes.decode("ascii")
        except UnicodeDecodeError as exc:
            raise ValueError(f"Invalid KMALL datagram type at offset {position}") from exc
        if not name.startswith("#"):
            raise ValueError(f"Invalid KMALL datagram type {name!r} at offset {position}")
        counts[name] += 1
        versions.setdefault(name, set()).add(version)
        if model:
            models.add(model)
        if name == "#MRZ":
            if version not in {0, 1, 2, 3}:
                raise ValueError(f"Unsupported KMALL #MRZ version {version} at offset {position}")
            body = data[position + _HEADER.size : position + size - 4]
            pings.append(_mrz(body, seconds, nanoseconds, position))
        else:
            skipped[name] += 1
        position += size

    notes = [SYNTHETIC_NOTICE]
    notes.extend(f"Skipped datagram {name}: {count}" for name, count in sorted(skipped.items()))
    notes.append("Backscatter source: MRZ reflectivity1_dB; no additional correction applied.")
    version_string = "; ".join(
        f"{name}=" + ",".join(str(value) for value in sorted(values))
        for name, values in sorted(versions.items())
    )
    return MultibeamRecord(
        source_format="KMALL",
        sonar_model=", ".join(f"EM{model}" for model in sorted(models)) or None,
        pings=pings,
        provenance=Provenance(
            source_path=str(source),
            sha256=file_sha256(source),
            reader="netsight.io.kmall.read_kmall",
            reader_version=READER_VERSION,
            notes=list(notes),
        ),
        record_counts=dict(counts),
        notes=notes,
        version=version_string,
        skipped_record_types=dict(skipped),
    )
