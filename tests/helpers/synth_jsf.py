"""Write small JSF files from the EdgeTech JSF Rev 1.8 layout (no external data)."""

from __future__ import annotations

import struct
from collections.abc import Sequence
from pathlib import Path

import numpy as np

from helpers.synth_xtf import seabed_row

HEADER = struct.Struct("<HBBHBBBBHI")
VALID_POSITION, VALID_HEADING, VALID_PITCH_ROLL, VALID_ALTITUDE = 0x1, 0x8, 0x20, 0x40
SPACING_INTERVAL_NS = 133_333  # 0.1 m slant spacing at 1500 m/s


def _frame(msg_type: int, subsystem: int, channel: int, body: bytes) -> bytes:
    return HEADER.pack(0x1601, 10, 0, msg_type, 2, subsystem, channel, 0, 0, len(body)) + body


def sonar_message(
    *,
    ping_number: int,
    channel: int,
    subsystem: int = 20,
    n_samples: int = 400,
    interval_ns: int = SPACING_INTERVAL_NS,
    start_depth: int = 0,
    t_s: int = 1_793_000_000,
    ms_today: int = 0,
    lon: float = 72.8,
    lat: float = 18.9,
    position_valid: bool = True,
    altitude_m: float = 5.0,
    heading_deg: float = 90.0,
    pitch_deg: float = 0.0,
    roll_deg: float = 0.0,
    weight: int = 0,
    data_format: int = 0,
    samples: Sequence[float] | None = None,
) -> bytes:
    body = bytearray(240)
    struct.pack_into("<i", body, 0, t_s)
    struct.pack_into("<I", body, 4, start_depth)
    struct.pack_into("<I", body, 8, ping_number)
    struct.pack_into("<H", body, 16, ((n_samples >> 16) & 0xF) << 8)
    struct.pack_into("<h", body, 28, 1)
    validity = VALID_HEADING | VALID_PITCH_ROLL | VALID_ALTITUDE
    if position_valid:
        validity |= VALID_POSITION
    struct.pack_into("<H", body, 30, validity)
    struct.pack_into("<h", body, 34, data_format)
    struct.pack_into("<i", body, 80, round(lon * 600_000))
    struct.pack_into("<i", body, 84, round(lat * 600_000))
    struct.pack_into("<h", body, 88, 2)
    struct.pack_into("<H", body, 114, n_samples & 0xFFFF)
    struct.pack_into("<I", body, 116, interval_ns)
    struct.pack_into("<i", body, 144, round(altitude_m * 1000))
    struct.pack_into("<h", body, 168, weight)
    struct.pack_into("<H", body, 172, round(heading_deg * 100) % 36000)
    struct.pack_into("<h", body, 174, round(pitch_deg * 32768 / 180))
    struct.pack_into("<h", body, 176, round(roll_deg * 32768 / 180))
    struct.pack_into("<I", body, 200, ms_today)
    if samples is None:
        samples = seabed_row(n_samples, interval_ns * 1e-9 * 750.0, altitude_m, ping=ping_number)
    values = np.asarray(samples, dtype=np.float64) * (2**weight)
    if data_format == 0:
        payload = np.clip(values, 0, 65535).astype("<u2").tobytes()
    else:
        iq = np.stack([values, np.zeros_like(values)], axis=1)
        payload = np.clip(iq, -32768, 32767).astype("<i2").tobytes()
    return _frame(80, subsystem, channel, bytes(body) + payload)


def nmea_message(t_s: int, ms: int, text: str) -> bytes:
    body = struct.pack("<iiB3x", t_s, ms, 2) + text.encode("ascii")
    return _frame(2002, 100, 0, body)


def write_synthetic_jsf(
    path: str | Path,
    *,
    n_pings: int = 8,
    n_samples: int = 400,
    one_sided_pings: Sequence[int] = (),
    **sonar_kwargs,
) -> Path:
    path = Path(path)
    out = bytearray()
    for p in range(n_pings):
        for channel in (0, 1):
            if channel == 1 and p in one_sided_pings:
                continue
            out += sonar_message(
                ping_number=1000 + p,
                channel=channel,
                n_samples=n_samples,
                t_s=1_793_000_000 + p,
                **sonar_kwargs,
            )
    path.write_bytes(bytes(out))
    return path
