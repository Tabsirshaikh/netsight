"""Generate small, valid XTF files with pyxtf's own ctypes structures (no external data)."""

from __future__ import annotations

import ctypes
from collections.abc import Sequence
from pathlib import Path

import numpy as np
from pyxtf import XTFFileHeader, XTFPingChanHeader, XTFPingHeader

WATER_VALUE = 5.0


def seabed_row(n_samples: int, spacing_m: float, altitude_m: float, ping: int = 0) -> np.ndarray:
    """Water column (low) until slant range reaches altitude, then textured seabed.

    Texture depends on sample index (so neighbouring pings correlate, like real seabed) plus a
    small deterministic per-ping perturbation.
    """
    i = np.arange(n_samples)
    slant = (i + 0.5) * spacing_m
    texture = 40.0 * np.sin(i * 0.3) + 20.0 * np.cos(i * 0.07)
    rng = np.random.default_rng(1000 + ping)
    row = 200.0 + texture + rng.normal(0.0, 3.0, n_samples)
    row[slant < altitude_m] = WATER_VALUE
    return np.clip(row, 0, 65535)


def write_synthetic_xtf(
    path: str | Path,
    *,
    n_pings: int = 12,
    n_samples: int = 500,
    slant_range_m: float = 50.0,
    altitude_m: float = 5.0,
    nav: str = "sensor",  # "sensor" | "ship" | "ship_layback" | "missing"
    nav_units: int = 3,
    weight: int = 0,
    layback_m: float = 50.0,
    rolls: Sequence[float] | None = None,
    ping_numbers: Sequence[int] | None = None,
    seconds: Sequence[int] | None = None,
    channel_types: Sequence[int] = (1, 2),
) -> Path:
    path = Path(path)
    fh = XTFFileHeader()
    fh.FileFormat = 123
    fh.SystemType = 1
    fh.SonarName = b"SYNTH"
    fh.NumberOfSonarChannels = len(channel_types)
    fh.NavUnits = nav_units
    for i, ctype in enumerate(channel_types):
        ci = fh.ChanInfo[i]
        ci.TypeOfChannel = ctype
        ci.SubChannelNumber = i
        ci.BytesPerSample = 2
        ci.SampleFormat = 3  # uint16
        ci.Frequency = 455.0
    buf = bytearray(bytes(fh))
    spacing = slant_range_m / n_samples
    for p in range(n_pings):
        ph = XTFPingHeader()
        ph.MagicNumber = 0xFACE
        ph.HeaderType = 0
        ph.NumChansToFollow = len(channel_types)
        record = ctypes.sizeof(XTFPingHeader) + len(channel_types) * (
            ctypes.sizeof(XTFPingChanHeader) + n_samples * 2
        )
        pad = (-record) % 64
        ph.NumBytesThisRecord = record + pad
        sec = seconds[p] if seconds is not None else p
        ph.Year, ph.Month, ph.Day = 2026, 11, 6
        ph.Hour, ph.Minute, ph.Second = 12, sec // 60, sec % 60
        ph.PingNumber = ping_numbers[p] if ping_numbers is not None else 100 + p
        lon, lat = 72.8 + p * 1e-5, 18.9
        if nav == "sensor":
            ph.SensorXcoordinate, ph.SensorYcoordinate = lon, lat
        elif nav in ("ship", "ship_layback"):
            ph.ShipXcoordinate, ph.ShipYcoordinate = lon, lat
            ph.Layback = layback_m if nav == "ship_layback" else 0.0
        ph.SensorPrimaryAltitude = altitude_m
        ph.SensorHeading = 90.0
        ph.SensorRoll = rolls[p] if rolls is not None else 0.0
        ph.SoundVelocity = 1500.0
        out = bytearray(bytes(ph))
        row = seabed_row(n_samples, spacing, altitude_m, ping=p)
        for c in range(len(channel_types)):
            ch = XTFPingChanHeader()
            ch.ChannelNumber = c
            ch.SlantRange = slant_range_m
            ch.NumSamples = n_samples
            ch.Frequency = 455
            ch.Weight = weight
            values = row * (2**weight) if weight else row
            out += bytes(ch) + np.clip(values, 0, 65535).astype(np.uint16).tobytes()
        out += b"\x00" * pad
        buf += out
    path.write_bytes(bytes(buf))
    return path
