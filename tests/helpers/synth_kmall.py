"""Independent KMALL Rev. H/I fixtures with deliberate nonmeasurement decoys."""

import struct
from pathlib import Path


def datagram(
    name: str,
    body: bytes,
    *,
    seconds: int = 1,
    nanoseconds: int = 123,
    version: int = 2,
) -> bytes:
    """Write a complete datagram with the required repeated length."""
    size = 20 + len(body) + 4
    return (
        struct.pack("<I4sBBHII", size, name.encode("ascii"), version, 1, 2040, seconds, nanoseconds)
        + body
        + struct.pack("<I", size)
    )


def mrz(
    *,
    seconds: int = 1,
    nanoseconds: int = 123,
    latitude: float = 12.5,
    longitude: float = -4.5,
    heading: float = 12.25,
    sound_speed: float = 1500.0,
    soundings: list[tuple[int, float, float, float, float]] | None = None,
    extra_soundings: list[tuple[int, float, float, float, float]] | None = None,
    extension: int = 0,
    partitions: int = 1,
    fans: int = 1,
) -> bytes:
    """Write tuples of (detection type, dB, depth, across, along).

    ``extension`` expands every length-delimited structure, ensuring readers
    actually use the declared lengths rather than one hard-coded stride.
    """
    if soundings is None:
        soundings = [(0, -25.5, 12.5, -3.0, 1.25), (2, -30.0, 20.0, 4.0, -2.0)]
    extras = extra_soundings or []
    common_size = 12 + extension
    common = bytearray(common_size)
    struct.pack_into("<HH8B", common, 0, common_size, 7, fans, 0, 1, 0, 0, 0, 1, 0)
    info_size = 152 + extension
    info = bytearray(info_size)
    struct.pack_into("<H", info, 0, info_size)
    struct.pack_into("<HHff", info, 92, 1, 48 + extension, heading, sound_speed)
    struct.pack_into("<dd", info, 124, latitude, longitude)
    tx = bytes(48 + extension)
    rx_size = 32 + extension
    sounding_size = 120 + extension
    rx = bytearray(rx_size)
    struct.pack_into(
        "<4H",
        rx,
        0,
        rx_size,
        len(soundings),
        sum(s[0] == 0 for s in soundings),
        sounding_size,
    )
    struct.pack_into("<3H", rx, 26, len(extras), 1, 4 + extension)
    class_info = bytes(4 + extension)
    encoded = bytearray()
    for index, (detection, reflectivity, depth, across, along) in enumerate(soundings + extras):
        sounding = bytearray(sounding_size)
        struct.pack_into("<HBB", sounding, 0, index, 0, detection)
        struct.pack_into("<f", sounding, 12, 777.0)  # rangeFactor, not reflectivity
        struct.pack_into("<f", sounding, 48, reflectivity)
        struct.pack_into("<f", sounding, 72, 888.0)  # beam angle, not depth
        struct.pack_into("<fff", sounding, 96, depth, across, along)
        encoded.extend(sounding)
    body = struct.pack("<HH", partitions, 1) + common + info + tx + rx + class_info + encoded
    return datagram("#MRZ", body, seconds=seconds, nanoseconds=nanoseconds)


def write_kmall(path: Path, datagrams: list[bytes] | None = None) -> Path:
    """Write two MRZ pings and an ignored installation datagram by default."""
    if datagrams is None:
        datagrams = [
            datagram("#IIP", b"installation", version=0),
            mrz(),
            mrz(
                seconds=2,
                nanoseconds=456,
                latitude=-3.0,
                longitude=2.0,
                heading=90.0,
                soundings=[(0, -10.0, 5.0, 2.0, 0.5)],
            ),
        ]
    path.write_bytes(b"".join(datagrams))
    return path
