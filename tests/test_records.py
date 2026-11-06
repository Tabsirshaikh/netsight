import numpy as np
import pytest

from netsight.core.hashing import file_sha256
from netsight.core.records import (
    CoordKind,
    NavSource,
    Ping,
    Provenance,
    SensorDescriptor,
    SensorType,
    SonarRecord,
)


def make_ping(i=0, n=100, slant=50.0, source=NavSource.SENSOR):
    return Ping(
        index=i,
        ping_number=100 + i,
        time=np.datetime64("2026-11-06T12:00:00") + np.timedelta64(i, "s"),
        x=72.8,
        y=18.9,
        coord_kind=CoordKind.LATLON,
        nav_source=source,
        heading_deg=90.0,
        pitch_deg=0.0,
        roll_deg=0.0,
        altitude_m=5.0,
        slant_range_m=slant,
        port=np.arange(n),
        stbd=np.arange(n) + 1,
    )


def make_record(pings):
    return SonarRecord(
        sensor=SensorDescriptor(SensorType.SIDESCAN, "xtf", model="SYNTH", frequency_khz=455.0),
        pings=pings,
        provenance=Provenance("x.xtf", "abc", "test", "0"),
    )


def test_ping_converts_arrays_to_float32_and_computes_spacing():
    p = make_ping(n=500, slant=50.0)
    assert p.port.dtype == np.float32 and p.stbd.dtype == np.float32
    assert p.n_samples == 500
    assert p.sample_spacing_m == pytest.approx(0.1)


def test_ping_rejects_mismatched_or_empty_channels():
    with pytest.raises(ValueError):
        Ping(**{**make_ping().__dict__, "stbd": np.arange(5)})
    with pytest.raises(ValueError):
        Ping(**{**make_ping().__dict__, "port": np.array([]), "stbd": np.array([])})


def test_ping_rejects_non_positive_slant_range():
    with pytest.raises(ValueError):
        Ping(**{**make_ping().__dict__, "slant_range_m": 0.0})


def test_channel_matrix_stacks_in_ping_order():
    rec = make_record([make_ping(0), make_ping(1)])
    m = rec.channel_matrix("stbd")
    assert m.shape == (2, 100)
    assert m[0, 0] == 1.0
    with pytest.raises(ValueError):
        rec.channel_matrix("bow")


def test_channel_matrix_rejects_uneven_sample_counts():
    rec = make_record([make_ping(0, n=100), make_ping(1, n=120)])
    with pytest.raises(ValueError):
        rec.channel_matrix("port")


def test_nav_source_counts_and_descriptor_dict():
    rec = make_record([make_ping(0), make_ping(1, source=NavSource.MISSING)])
    assert rec.nav_source_counts() == {"sensor": 1, "missing": 1}
    assert rec.n_pings == 2
    d = rec.sensor.to_dict()
    assert d["sensor_type"] == "sidescan" and d["frequency_khz"] == 455.0


def test_file_sha256(tmp_path):
    f = tmp_path / "a.bin"
    f.write_bytes(b"netsight")
    assert file_sha256(f) == "210815b8e7b5cca0487bb1bd85ad8a96351e89483362785697e504008302e629"
