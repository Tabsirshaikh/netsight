import math

import numpy as np
import pytest
from helpers.synth_jsf import nmea_message, sonar_message, write_synthetic_jsf
from helpers.synth_xtf import seabed_row

from netsight.core.records import CoordKind, NavSource
from netsight.io.jsf import JsfFormatError, read_jsf


def _expected_row():
    row = seabed_row(400, 133_333e-9 * 750.0, 5.0, ping=1000)
    return np.clip(row, 0, 65535).astype(np.uint16)


def test_reads_two_sided_pings(tmp_path):
    rec = read_jsf(write_synthetic_jsf(tmp_path / "a.jsf", n_pings=5, n_samples=400))
    assert rec.n_pings == 5
    assert rec.sensor.source_format == "jsf"
    p = rec.pings[0]
    assert p.ping_number == 1000
    assert p.n_samples == 400
    assert p.slant_range_m == pytest.approx(400 * 133_333e-9 * 750.0)
    assert p.altitude_m == pytest.approx(5.0)
    assert p.heading_deg == pytest.approx(90.0)
    np.testing.assert_array_equal(p.port, _expected_row().astype(np.float32))


def test_position_from_message_80_is_flagged_as_ship(tmp_path):
    rec = read_jsf(write_synthetic_jsf(tmp_path / "p.jsf", n_pings=2))
    p = rec.pings[0]
    assert p.nav_source == NavSource.SHIP and p.coord_kind == CoordKind.LATLON
    assert p.x == pytest.approx(72.8, abs=1e-6) and p.y == pytest.approx(18.9, abs=1e-6)
    assert any("not time-interpolated" in n for n in rec.provenance.notes)


def test_nmea_fallback_when_position_invalid(tmp_path):
    f = tmp_path / "n.jsf"
    gga = "$GPGGA,120000.00,1854.00,N,07248.00,E,1,08,0.9,1.0,M,,M,,*47"
    data = nmea_message(1_793_000_000, 0, gga)
    data += sonar_message(ping_number=1, channel=0, position_valid=False)
    data += sonar_message(ping_number=1, channel=1, position_valid=False)
    f.write_bytes(data)
    p = read_jsf(f).pings[0]
    assert p.nav_source == NavSource.SHIP
    assert p.y == pytest.approx(18.9) and p.x == pytest.approx(72.8)


def test_missing_position_is_withdrawn(tmp_path):
    f = write_synthetic_jsf(tmp_path / "m.jsf", n_pings=2, position_valid=False)
    p = read_jsf(f).pings[0]
    assert p.nav_source == NavSource.MISSING and math.isnan(p.x)


def test_weighting_and_one_sided_pings(tmp_path):
    f = write_synthetic_jsf(tmp_path / "w.jsf", n_pings=4, weight=1, one_sided_pings=(2,))
    rec = read_jsf(f)
    assert [p.ping_number for p in rec.pings] == [1000, 1001, 1003]
    assert any("one side only" in n for n in rec.provenance.notes)
    np.testing.assert_allclose(rec.pings[0].port, _expected_row(), atol=1.0)


def test_start_depth_prepends_nan(tmp_path):
    rec = read_jsf(write_synthetic_jsf(tmp_path / "s.jsf", n_pings=1, start_depth=20))
    p = rec.pings[0]
    assert p.n_samples == 420
    assert np.isnan(p.port[:20]).all() and np.isfinite(p.port[20:]).all()


def test_analytic_format_becomes_magnitude(tmp_path):
    rec = read_jsf(write_synthetic_jsf(tmp_path / "iq.jsf", n_pings=1, data_format=1))
    # generator writes I=value, Q=0, so the magnitude equals the envelope row
    np.testing.assert_array_equal(rec.pings[0].port, _expected_row().astype(np.float32))


def test_analytic_format_uses_both_i_and_q(tmp_path):
    f = tmp_path / "iq34.jsf"
    pairs = [(3, 4), (-3, 4), (0, -5), (6, 8)]
    data = b"".join(
        sonar_message(ping_number=1, channel=c, n_samples=4, data_format=1, iq=pairs)
        for c in (0, 1)
    )
    f.write_bytes(data)
    p = read_jsf(f).pings[0]
    np.testing.assert_allclose(p.port, [5, 5, 5, 10])
    np.testing.assert_allclose(p.stbd, [5, 5, 5, 10])


def test_duplicate_sonar_message_keeps_first_and_is_noted(tmp_path):
    f = tmp_path / "dup.jsf"
    first = [100.0] * 8
    second = [900.0] * 8
    data = sonar_message(ping_number=7, channel=0, n_samples=8, samples=first)
    data += sonar_message(ping_number=7, channel=0, n_samples=8, samples=second)
    data += sonar_message(ping_number=7, channel=1, n_samples=8, samples=first)
    f.write_bytes(data)
    rec = read_jsf(f)
    assert rec.n_pings == 1
    np.testing.assert_array_equal(rec.pings[0].port, np.full(8, 100.0, dtype=np.float32))
    assert any(
        "duplicate sonar message ignored (multi-packet pings unsupported)" in n and "(1 pings)" in n
        for n in rec.provenance.notes
    )


def test_absurd_start_depth_raises_naming_ping(tmp_path):
    f = tmp_path / "deep.jsf"
    data = sonar_message(ping_number=42, channel=0, n_samples=8, start_depth=10_000_001)
    data += sonar_message(ping_number=42, channel=1, n_samples=8)
    f.write_bytes(data)
    with pytest.raises(JsfFormatError, match="ping 42"):
        read_jsf(f)


def test_bad_marker_and_truncation_raise(tmp_path):
    bad = tmp_path / "bad.jsf"
    bad.write_bytes(b"\x00" * 32)
    with pytest.raises(JsfFormatError):
        read_jsf(bad)
    trunc = tmp_path / "trunc.jsf"
    trunc.write_bytes(sonar_message(ping_number=1, channel=0)[:-10])
    with pytest.raises(JsfFormatError):
        read_jsf(trunc)
