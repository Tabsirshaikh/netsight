import math

import numpy as np
import pytest
from helpers.synth_xtf import seabed_row, write_synthetic_xtf

from netsight.core.records import CoordKind, NavSource, SensorType
from netsight.io.xtf import UnsafeIndexFileError, XtfFormatError, read_xtf


def test_reads_pings_channels_and_sensor_nav(tmp_path):
    f = write_synthetic_xtf(tmp_path / "a.xtf", n_pings=6, n_samples=500)
    rec = read_xtf(f)
    assert rec.n_pings == 6
    assert rec.sensor.sensor_type == SensorType.SIDESCAN
    assert rec.sensor.source_format == "xtf"
    assert rec.sensor.model == "SYNTH"
    assert rec.sensor.frequency_khz == pytest.approx(455.0)
    p = rec.pings[0]
    assert p.nav_source == NavSource.SENSOR and p.coord_kind == CoordKind.LATLON
    assert p.x == pytest.approx(72.8) and p.y == pytest.approx(18.9)
    assert p.slant_range_m == pytest.approx(50.0)
    assert p.altitude_m == pytest.approx(5.0)
    expected = np.clip(seabed_row(500, 0.1, 5.0, ping=0), 0, 65535).astype(np.uint16)
    np.testing.assert_array_equal(p.port, expected.astype(np.float32))
    assert len(rec.provenance.sha256) == 64
    assert rec.provenance.reader == "netsight.io.xtf"


def test_weight_is_applied(tmp_path):
    f = write_synthetic_xtf(tmp_path / "w.xtf", n_pings=2, weight=2)
    p = read_xtf(f).pings[0]
    expected = np.clip(seabed_row(500, 0.1, 5.0, ping=0), 0, 65535).astype(np.uint16)
    np.testing.assert_allclose(p.port, expected, atol=1.0)  # uint16 truncation of 4x values


@pytest.mark.parametrize(
    ("nav", "source"),
    [
        ("ship", NavSource.SHIP),
        ("ship_layback", NavSource.SHIP_LAYBACK),
        ("missing", NavSource.MISSING),
    ],
)
def test_nav_sources(tmp_path, nav, source):
    rec = read_xtf(write_synthetic_xtf(tmp_path / f"{nav}.xtf", n_pings=3, nav=nav))
    assert {p.nav_source for p in rec.pings} == {source}
    if source == NavSource.MISSING:
        assert math.isnan(rec.pings[0].x)
    assert rec.nav_source_counts() == {str(source): 3}


def test_projected_nav_units(tmp_path):
    rec = read_xtf(write_synthetic_xtf(tmp_path / "m.xtf", n_pings=2, nav_units=0))
    assert rec.pings[0].coord_kind == CoordKind.PROJECTED


def test_pings_sorted_by_time(tmp_path):
    f = write_synthetic_xtf(
        tmp_path / "o.xtf", n_pings=3, seconds=[5, 1, 3], ping_numbers=[3, 1, 2]
    )
    rec = read_xtf(f)
    assert [p.ping_number for p in rec.pings] == [1, 2, 3]
    assert [p.index for p in rec.pings] == [0, 1, 2]


def test_refuses_pickle_index_file(tmp_path):
    f = write_synthetic_xtf(tmp_path / "i.xtf", n_pings=2)
    (tmp_path / "i.pyxtf_idx").write_bytes(b"not trusted")
    with pytest.raises(UnsafeIndexFileError):
        read_xtf(f)


def test_requires_port_and_starboard(tmp_path):
    f = write_synthetic_xtf(tmp_path / "s.xtf", n_pings=2, channel_types=(0, 0))
    with pytest.raises(XtfFormatError):
        read_xtf(f)


@pytest.mark.parametrize("channel_types", [(0, 1, 2), (1, 2, 0)])
def test_mixed_channel_file_never_raises_bare_error_or_swaps_channels(tmp_path, channel_types):
    # pyxtf filters ChanInfo to port/stbd for decoding, so a third (sub-bottom) channel in the
    # ping records makes pyxtf raise IndexError; the reader must report that as XtfFormatError.
    f = write_synthetic_xtf(tmp_path / "mixed.xtf", n_pings=2, channel_types=channel_types)
    with pytest.raises(XtfFormatError, match=r"mixed\.xtf"):
        read_xtf(f)


@pytest.mark.parametrize("channel_types", [(1,), (1, 0)])
def test_port_only_file_is_rejected(tmp_path, channel_types):
    f = write_synthetic_xtf(tmp_path / "port.xtf", n_pings=2, channel_types=channel_types)
    with pytest.raises(XtfFormatError):
        read_xtf(f)


def test_channel_identity_mismatch_skips_pings_then_raises(tmp_path):
    # Header says channel 0 = port, 1 = stbd, but the pings label them the other way round.
    f = write_synthetic_xtf(tmp_path / "swap.xtf", n_pings=3, channel_numbers=(1, 0))
    with pytest.raises(XtfFormatError, match="channel identity mismatch"):
        read_xtf(f)


def test_channel_number_out_of_range_is_not_a_bare_error(tmp_path):
    f = write_synthetic_xtf(tmp_path / "oor.xtf", n_pings=2, channel_numbers=(0, 9))
    with pytest.raises(XtfFormatError):
        read_xtf(f)


def test_identity_mismatch_on_some_pings_is_counted_in_notes(tmp_path):
    good = write_synthetic_xtf(tmp_path / "g.xtf", n_pings=4)
    raw = bytearray(good.read_bytes())
    # Corrupt nothing structurally; instead build a file where only some pings are fine by
    # concatenating a swapped-label file's ping records after a good file.
    swapped = write_synthetic_xtf(tmp_path / "s.xtf", n_pings=2, channel_numbers=(1, 0))
    header_len = len(raw) - 4 * _record_len()
    raw += swapped.read_bytes()[header_len:]
    mixed = tmp_path / "partial.xtf"
    mixed.write_bytes(bytes(raw))
    rec = read_xtf(mixed)
    assert rec.n_pings == 4
    assert any("channel identity mismatch (2 pings)" in n for n in rec.provenance.notes)


def test_corrupt_date_skips_ping_and_is_counted(tmp_path):
    f = write_synthetic_xtf(tmp_path / "d.xtf", n_pings=4, months=[11, 13, 11, 11])
    rec = read_xtf(f)
    assert rec.n_pings == 3
    assert any("invalid timestamp (1 pings)" in n for n in rec.provenance.notes)


def test_truncated_or_empty_file_raises_format_error(tmp_path):
    empty = tmp_path / "empty.xtf"
    empty.write_bytes(b"")
    with pytest.raises(XtfFormatError, match=r"empty\.xtf"):
        read_xtf(empty)
    junk = tmp_path / "junk.xtf"
    junk.write_bytes(b"\x01" * 10)
    with pytest.raises(XtfFormatError, match=r"junk\.xtf"):
        read_xtf(junk)


def _record_len(n_samples: int = 500, n_chans: int = 2) -> int:
    import ctypes

    from pyxtf import XTFPingChanHeader, XTFPingHeader

    record = ctypes.sizeof(XTFPingHeader) + n_chans * (
        ctypes.sizeof(XTFPingChanHeader) + n_samples * 2
    )
    return record + (-record) % 64
