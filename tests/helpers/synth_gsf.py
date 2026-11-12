"""Independent, small GSF writers for reader tests."""

import struct
from pathlib import Path


def record(identifier: int, payload: bytes, *, checksum: bool = False) -> bytes:
    """Wrap one payload, including an optional checksum word and alignment."""
    word = identifier | (0x80000000 if checksum else 0)
    return (
        struct.pack(">II", len(payload), word)
        + (b"\x12\x34\x56\x78" if checksum else b"")
        + payload
        + b"\0" * ((-len(payload)) % 4)
    )


def subrecord(identifier: int, payload: bytes) -> bytes:
    """Wrap one unpadded subrecord."""
    return struct.pack(">I", identifier << 24 | len(payload)) + payload


def scale_factors(factors: list[tuple[int, int, int, int]]) -> bytes:
    """Write (id, width flag, multiplier, offset) entries."""
    payload = struct.pack(">i", len(factors))
    for identifier, flag, multiplier, offset in factors:
        payload += struct.pack(">Iii", identifier << 24 | flag, multiplier, offset)
    return subrecord(21, payload)


def ping(
    *,
    seconds: int = 1,
    nanoseconds: int = 123,
    longitude_raw: int = -45_000_000,
    latitude_raw: int = 125_000_000,
    heading_raw: int = 1234,
    beams: int = 2,
    subrecords: bytes = b"",
) -> bytes:
    """Write the 56-byte v3 ping header followed by supplied subrecords."""
    header = (
        struct.pack(">4i", seconds, nanoseconds, longitude_raw, latitude_raw)
        + struct.pack(">5h", beams, 0, 0, 0, 0)
        + struct.pack(">iH", 0, heading_raw)
        + struct.pack(">3h2H", 0, 0, 0, 0, 0)
        + struct.pack(">3ih", 0, 0, 0, 0)
    )
    assert len(header) == 56
    return record(2, header + subrecords)


def write_gsf(path: Path, records: list[bytes] | None = None) -> Path:
    """Write a header and, by default, two scaled pings with carried factors."""
    if records is None:
        factors = scale_factors([(1, 0, 100, 0), (2, 0, 10, 1), (3, 0, 10, -2), (6, 0, 10, 0)])
        first = (
            factors
            + subrecord(1, struct.pack(">2H", 1234, 2000))
            + subrecord(2, struct.pack(">2h", -20, 30))
            + subrecord(3, struct.pack(">2h", 10, -10))
            + subrecord(6, struct.pack(">2h", -250, -300))
            + subrecord(16, b"\0\x01")
            + subrecord(99, b"odd")
        )
        second = (
            subrecord(1, struct.pack(">H", 500))
            + subrecord(2, struct.pack(">h", 20))
            + subrecord(6, struct.pack(">h", -100))
        )
        records = [
            ping(subrecords=first),
            record(7, b"abc", checksum=True),
            ping(
                seconds=2,
                nanoseconds=456,
                longitude_raw=20_000_000,
                latitude_raw=-30_000_000,
                heading_raw=9000,
                beams=1,
                subrecords=second,
            ),
        ]
    path.write_bytes(record(1, b"GSF-v03.10\0") + b"".join(records))
    return path
