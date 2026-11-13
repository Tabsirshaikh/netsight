"""Regression test on a real NOAA GSF file (CC_BlockA03, Reson 7125, public domain): the
header records and pings 0, 124 and 125 of 1A03-FILL-003.gsf.mb121 from NCEI
(data.ngdc.noaa.gov/platforms/ocean/ships/quicksilver/CC_BlockA03_quicksilver/...).
The reader was first
written against synthetic files only and could not read real GSF (scale factors are
subrecord 100, not 21)."""

import struct
from pathlib import Path

import numpy as np

from netsight.io.gsf import read_gsf

DATA = Path(__file__).parent / "data" / "noaa_cc_blocka03_3pings.gsf"


def _first_ping_beam(beam: int) -> float:
    """Depth of one beam decoded by hand from the published format."""
    data = DATA.read_bytes()
    pos = 0
    while True:
        size, word = struct.unpack_from(">II", data, pos)
        pos += 8 + (4 if word & 0x80000000 else 0)
        body = data[pos : pos + size]
        pos += size + (-size) % 4
        if word & 0x3FFFFF == 2:
            break
    p, scale, raw = 56, None, None
    while p < len(body):
        w = struct.unpack_from(">I", body, p)[0]
        sid, ssz = w >> 24, w & 0xFFFFFF
        if sid == 100:  # scale factors: count, then (id/flag word, multiplier, offset)
            for i in range(struct.unpack_from(">i", body, p + 4)[0]):
                e = struct.unpack_from(">Iii", body, p + 8 + 12 * i)
                if e[0] >> 24 == 1:
                    scale = (e[1], e[2])
        if sid == 1:
            raw = struct.unpack_from(">H", body, p + 4 + 2 * beam)[0]
        p += 4 + ssz
    return raw / scale[0] - scale[1]


def test_real_noaa_gsf_reads_three_pings_with_correct_depths():
    rec = read_gsf(DATA)
    assert len(rec.pings) == 3
    p = rec.pings[0]
    assert len(p.depth) == 256
    assert p.depth[128] == _first_ping_beam(128)
    assert 10 < np.median(p.depth) < 100  # coastal survey depths in metres
    assert 30 < p.latitude < 40 and -125 < p.longitude < -115  # California central coast
    assert np.isfinite(p.across_track).all()
    # flags in this file are 0x00 (accepted sounding) or 0x05 (not selected); only 0x00 is valid
    flags = np.concatenate([q.beam_flags for q in rec.pings])
    assert set(np.unique(flags)) <= {0, 5}
    valid = np.concatenate([q.valid for q in rec.pings])
    assert valid.sum() == (flags == 0).sum() > 0


def test_record_names_follow_gsf_h():
    rec = read_gsf(DATA)
    assert rec.record_counts["HEADER"] == 1 and rec.record_counts["SWATH_BATHYMETRY_PING"] == 3
    names = set(rec.record_counts)
    assert "SOUND_VELOCITY_PROFILE" in names or "PROCESSING_PARAMETERS" in names
    assert not any(n.startswith("UNKNOWN") for n in names)
