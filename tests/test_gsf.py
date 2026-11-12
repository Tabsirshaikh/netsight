"""Hand-computed tests for GSF framing, scales, missing data, and provenance."""

import hashlib
import struct
from dataclasses import FrozenInstanceError
from pathlib import Path

import numpy as np
import pytest
from helpers.synth_gsf import ping, record, scale_factors, subrecord, write_gsf

from netsight.io.gsf import read_gsf


def test_gsf_navigation_scales_counts_and_provenance(tmp_path: Path) -> None:
    path = write_gsf(tmp_path / "small.gsf")
    result = read_gsf(path)
    assert result.source_format == "GSF"
    assert result.version == "GSF-v03.10"
    assert result.number_of_pings == 2
    assert result.sonar_model is None
    assert result.record_counts == {
        "HEADER": 1,
        "SWATH_BATHYMETRY_PING": 2,
        "COMMENT": 1,
    }
    assert result.skipped_record_types == {"subrecord:99": 1, "COMMENT": 1}
    assert any("subrecord:99: 1" in note for note in result.notes)
    assert any("Checksum words consumed without verification: 1" in n for n in result.notes)
    assert any("MEAN_CAL_AMPLITUDE: 2 pings" in n for n in result.notes)
    assert result.provenance.source_path == str(path)
    assert result.provenance.sha256 == hashlib.sha256(path.read_bytes()).hexdigest()
    assert result.provenance.reader == "netsight.io.gsf.read_gsf"
    assert result.provenance.reader_version
    assert result.provenance.notes == result.notes

    first, second = result.pings
    assert first.time == np.datetime64("1970-01-01T00:00:01.000000123", "ns")
    assert second.time == np.datetime64("1970-01-01T00:00:02.000000456", "ns")
    assert first.time.dtype == np.dtype("datetime64[ns]")
    assert (first.latitude, first.longitude, first.heading) == (12.5, -4.5, 12.34)
    assert (second.latitude, second.longitude, second.heading) == (-3.0, 2.0, 90.0)
    assert result.nav_source == "sensor"
    assert np.isnan(first.sound_speed)
    # 1234 / 100 = 12.34; -20 / 10 - 1 = -3; 10 / 10 - (-2) = 3.
    np.testing.assert_allclose(first.depth, [12.34, 20.0])
    np.testing.assert_array_equal(first.across_track, [-3.0, 2.0])
    np.testing.assert_array_equal(first.along_track, [3.0, 1.0])
    np.testing.assert_array_equal(first.backscatter, [-25.0, -30.0])
    np.testing.assert_array_equal(first.valid, [True, False])
    np.testing.assert_array_equal(first.beam_flags, [0, 1])
    # The second ping contains no SCALE_FACTORS.
    np.testing.assert_array_equal(second.depth, [5.0])
    np.testing.assert_array_equal(second.across_track, [1.0])
    np.testing.assert_array_equal(second.backscatter, [-10.0])
    assert np.isnan(second.along_track).all()
    np.testing.assert_array_equal(second.valid, [True])
    assert second.beam_flags is None
    for array in (first.depth, first.across_track, first.along_track, first.backscatter):
        assert array.dtype == np.float64
    assert first.valid.dtype == np.bool_
    np.testing.assert_allclose(
        result.backscatter_matrix(), [[-25.0, -30.0], [-10.0, np.nan]], equal_nan=True
    )


@pytest.mark.parametrize(
    ("flag", "unsigned_format", "signed_format", "raw", "expected"),
    [
        (0x10, ">B", ">b", 123, 10.3),
        (0, ">H", ">h", 1234, 121.4),
        (0x20, ">I", ">i", 123456, 12343.6),
        (0x100000, ">B", ">b", 123, 10.3),
    ],
)
def test_widths_offsets_and_relative_amplitude(
    tmp_path: Path,
    flag: int,
    unsigned_format: str,
    signed_format: str,
    raw: int,
    expected: float,
) -> None:
    data = (
        scale_factors([(1, flag, 10, 2), (7, flag, 2, -1)])
        + subrecord(1, struct.pack(unsigned_format, raw))
        + subrecord(7, struct.pack(signed_format, -12))
    )
    result = read_gsf(write_gsf(tmp_path / "width.gsf", [ping(beams=1, subrecords=data)]))
    assert result.pings[0].depth[0] == pytest.approx(expected)
    # -12 / 2 - (-1) = -5.
    np.testing.assert_array_equal(result.pings[0].backscatter, [-5.0])
    assert any("MEAN_REL_AMPLITUDE: 1 pings" in note for note in result.notes)


def test_calibrated_amplitude_preferred_and_unknowns_counted(tmp_path: Path) -> None:
    data = (
        scale_factors([(6, 0, 10, 0), (7, 0, 10, 0)])
        + subrecord(6, struct.pack(">h", -200))
        + subrecord(7, struct.pack(">h", -300))
        + subrecord(99, b"x")
        + subrecord(99, b"yz")
        + subrecord(128, b"sensor")
    )
    result = read_gsf(
        write_gsf(
            tmp_path / "unknown.gsf",
            [record(99, b"?"), ping(beams=1, subrecords=data)],
        )
    )
    np.testing.assert_array_equal(result.pings[0].backscatter, [-20.0])
    assert result.record_counts["UNKNOWN_99"] == 1
    assert result.skipped_record_types == {"UNKNOWN_99": 1, "subrecord:99": 2, "subrecord:128": 1}
    assert result.sonar_model == "GSF sensor id 128"


def test_missing_values_and_empty_record(tmp_path: Path) -> None:
    result = read_gsf(
        write_gsf(
            tmp_path / "missing.gsf",
            [ping(latitude_raw=910_000_000, longitude_raw=1_810_000_000, heading_raw=36100)],
        )
    )
    beam = result.pings[0]
    assert np.isnan([beam.latitude, beam.longitude, beam.heading, beam.sound_speed]).all()
    assert result.nav_source == "missing"
    assert np.isnan(beam.depth).all()
    assert np.isnan(beam.backscatter).all()
    np.testing.assert_array_equal(beam.valid, [True, True])
    empty = read_gsf(write_gsf(tmp_path / "empty.gsf", []))
    assert empty.number_of_pings == 0
    assert empty.nav_source == "missing"
    assert empty.backscatter_matrix().shape == (0, 0)


@pytest.mark.parametrize(
    ("data", "message"),
    [
        (subrecord(1, b"\0\1"), "no scale factor"),
        (scale_factors([(1, 0, 0, 0)]), "multiplier must be positive"),
        (
            scale_factors([(1, 1, 1, 0)]) + subrecord(1, b"\0\1"),
            "unsupported compression",
        ),
        (
            scale_factors([(1, 0, 1, 0)]) + subrecord(1, b"\0"),
            "array size does not match",
        ),
        (subrecord(16, b""), "BEAM_FLAGS size"),
        (struct.pack(">I", (99 << 24) | 100), "Truncated"),
    ],
)
def test_bad_subrecords_raise(tmp_path: Path, data: bytes, message: str) -> None:
    path = write_gsf(tmp_path / "bad.gsf", [ping(beams=1, subrecords=data)])
    with pytest.raises(ValueError, match=message):
        read_gsf(path)


def test_bad_time_truncation_and_version(tmp_path: Path) -> None:
    path = write_gsf(tmp_path / "time.gsf", [ping(nanoseconds=-1)])
    with pytest.raises(ValueError, match="nanoseconds"):
        read_gsf(path)
    path.write_bytes(record(1, b"GSF-v02.10"))
    with pytest.raises(ValueError, match="Unsupported GSF version"):
        read_gsf(path)
    path.write_bytes(struct.pack(">II", 10, 0x80000007) + b"\0\0")
    with pytest.raises(ValueError, match="checksum"):
        read_gsf(path)
    path.write_bytes(record(1, b"GSF-v03.10")[:-1])
    with pytest.raises(ValueError, match="padding"):
        read_gsf(path)
    path.write_bytes(b"")
    with pytest.raises(ValueError, match="Missing GSF"):
        read_gsf(path)


def test_ping_is_frozen_and_arrays_are_defensive(tmp_path: Path) -> None:
    result = read_gsf(write_gsf(tmp_path / "frozen.gsf"))
    beam = result.pings[0]
    with pytest.raises(FrozenInstanceError):
        beam.heading = 0.0  # type: ignore[misc]
    with pytest.raises(ValueError, match="read-only"):
        beam.depth[0] = 0.0
    matrix = result.backscatter_matrix()
    matrix[0, 0] = 0.0
    assert beam.backscatter[0] == -25.0
