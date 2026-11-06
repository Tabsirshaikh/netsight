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
