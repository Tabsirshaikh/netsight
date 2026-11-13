"""Independent, hand-computed tests of KMALL structure offsets and framing."""

import hashlib
import struct
from pathlib import Path

import numpy as np
import pytest
from helpers.synth_kmall import datagram, mrz, write_kmall

from netsight.io.kmall import read_kmall


def test_mrz_navigation_soundings_counts_and_provenance(tmp_path: Path) -> None:
    path = write_kmall(tmp_path / "small.kmall")
    result = read_kmall(path)
    assert result.source_format == "KMALL"
    assert result.version == "#IIP=0; #MRZ=2"
    assert result.sonar_model == "EM2040"
    assert result.number_of_pings == 2
    assert result.record_counts == {"#IIP": 1, "#MRZ": 2}
    assert result.skipped_record_types == {"#IIP": 1}
    assert any("Skipped datagram #IIP: 1" in note for note in result.notes)
    assert result.provenance.source_path == str(path)
    assert result.provenance.sha256 == hashlib.sha256(path.read_bytes()).hexdigest()
    assert result.provenance.reader == "netsight.io.kmall.read_kmall"
    assert result.provenance.reader_version
    assert result.provenance.notes == result.notes

    first, second = result.pings
    assert first.time == np.datetime64("1970-01-01T00:00:01.000000123", "ns")
    assert second.time == np.datetime64("1970-01-01T00:00:02.000000456", "ns")
    assert first.time.dtype == np.dtype("datetime64[ns]")
    assert (first.latitude, first.longitude, first.heading) == (12.5, -4.5, 12.25)
    assert (second.latitude, second.longitude, second.heading) == (-3.0, 2.0, 90.0)
    assert first.sound_speed == 1500.0
    assert result.nav_source == "sensor"

    # The writer puts decoys 777 and 888 at offsets 12 and 72 respectively.
    np.testing.assert_array_equal(first.backscatter, [-25.5, -30.0])
    np.testing.assert_array_equal(first.depth, [12.5, 20.0])
    np.testing.assert_array_equal(first.across_track, [-3.0, 4.0])
    np.testing.assert_array_equal(first.along_track, [1.25, -2.0])
    np.testing.assert_array_equal(first.valid, [True, False])
    np.testing.assert_array_equal(first.beam_flags, [0, 2])
    np.testing.assert_array_equal(second.depth, [5.0])
    np.testing.assert_array_equal(second.across_track, [2.0])
    np.testing.assert_array_equal(second.along_track, [0.5])
    for array in (first.depth, first.across_track, first.along_track, first.backscatter):
        assert array.dtype == np.float64
    np.testing.assert_allclose(
        result.backscatter_matrix(), [[-25.5, -30.0], [-10.0, np.nan]], equal_nan=True
    )


def test_declared_lengths_extra_detections_and_sample_tail(tmp_path: Path) -> None:
    encoded = bytearray(
        mrz(
            extension=8,
            soundings=[(0, -20.0, 10.0, -2.0, 1.0)],
            extra_soundings=[(1, -40.0, 30.0, 6.0, -1.0)],
        )
    )
    # Header 20 + partition 4 + common 20 + pingInfo 160 + tx 56
    # + rxInfo 40 + classInfo 12 = sounding offset 312.
    struct.pack_into("<H", encoded, 312 + 116, 2)
    # Replace the trailer with two int16 samples and a new trailer.
    encoded = encoded[:-4] + struct.pack("<2h", -100, -200) + b"\0" * 4
    struct.pack_into("<I", encoded, 0, len(encoded))
    struct.pack_into("<I", encoded, len(encoded) - 4, len(encoded))
    result = read_kmall(write_kmall(tmp_path / "extended.kmall", [bytes(encoded)]))
    beam = result.pings[0]
    np.testing.assert_array_equal(beam.depth, [10.0, 30.0])
    np.testing.assert_array_equal(beam.backscatter, [-20.0, -40.0])
    np.testing.assert_array_equal(beam.across_track, [-2.0, 6.0])
    np.testing.assert_array_equal(beam.along_track, [1.0, -1.0])
    np.testing.assert_array_equal(beam.valid, [True, True])


def test_every_non_mrz_type_is_counted_and_skipped(tmp_path: Path) -> None:
    records = [
        datagram("#IOP", b"a"),
        datagram("#SPO", b"b"),
        datagram("#IOP", b"c"),
        datagram("#XYZ", b"unknown"),
    ]
    result = read_kmall(write_kmall(tmp_path / "skip.kmall", records))
    assert result.record_counts == {"#IOP": 2, "#SPO": 1, "#XYZ": 1}
    assert result.skipped_record_types == result.record_counts
    assert result.pings == []
    assert result.nav_source == "missing"
    assert result.backscatter_matrix().shape == (0, 0)
    assert any("Skipped datagram #IOP: 2" in n for n in result.notes)


def test_missing_navigation_and_measurements_remain_nan(tmp_path: Path) -> None:
    records = [
        mrz(),
        mrz(
            latitude=float("nan"),
            longitude=181.0,
            heading=361.0,
            sound_speed=0.0,
            soundings=[(0, float("nan"), float("nan"), float("nan"), float("nan"))],
        ),
    ]
    result = read_kmall(write_kmall(tmp_path / "missing.kmall", records))
    beam = result.pings[1]
    assert result.nav_source == "missing"
    assert np.isnan([beam.latitude, beam.longitude, beam.heading, beam.sound_speed]).all()
    for values in (beam.depth, beam.across_track, beam.along_track, beam.backscatter):
        assert np.isnan(values).all()
    np.testing.assert_array_equal(beam.valid, [True])


def test_trailing_length_mismatch_reports_datagram_offset(tmp_path: Path) -> None:
    prefix = datagram("#IIP", b"abc")
    broken = bytearray(mrz())
    struct.pack_into("<I", broken, len(broken) - 4, 999)
    path = write_kmall(tmp_path / "broken.kmall", [prefix, bytes(broken)])
    with pytest.raises(ValueError, match=rf"trailing-length mismatch at offset {len(prefix)}"):
        read_kmall(path)


@pytest.mark.parametrize(
    ("encoded", "message"),
    [
        (mrz(partitions=2), "multipart"),
        (mrz(nanoseconds=1_000_000_000), "nanoseconds"),
        (mrz()[:-5], "Truncated"),
        (b"", "Empty KMALL"),
        (struct.pack("<I", 4) + b"\0" * 16, "Invalid KMALL datagram length"),
    ],
)
def test_invalid_datagrams_raise(tmp_path: Path, encoded: bytes, message: str) -> None:
    path = write_kmall(tmp_path / "bad.kmall", [encoded])
    with pytest.raises(ValueError, match=message):
        read_kmall(path)


@pytest.mark.parametrize(
    ("offset", "value", "message"),
    [
        (24, 10, "numBytesCmnPart"),
        (36, 100, "pingInfo is too short"),
        (236, 20, "numBytesRxInfo"),
        (242, 80, "numBytesPerSounding"),
    ],
)
def test_invalid_structure_lengths_raise(
    tmp_path: Path, offset: int, value: int, message: str
) -> None:
    # Default absolute offsets: common=24, info=36, tx=188, rx=236.
    encoded = bytearray(mrz())
    struct.pack_into("<H", encoded, offset, value)
    path = write_kmall(tmp_path / "length.kmall", [bytes(encoded)])
    with pytest.raises(ValueError, match=message):
        read_kmall(path)


def test_unknown_mrz_version_rejected(tmp_path: Path) -> None:
    encoded = bytearray(mrz())
    encoded[8] = 99
    with pytest.raises(ValueError, match="Unsupported KMALL #MRZ version 99"):
        read_kmall(write_kmall(tmp_path / "version.kmall", [bytes(encoded)]))


def test_missing_path_is_value_error(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="Cannot read multibeam source"):
        read_kmall(tmp_path / "absent.kmall")


def test_multi_fan_pings_are_joined_into_one_ping(tmp_path: Path) -> None:
    """Real Kongsberg systems (EM304, EM2040 dual swath) write one MRZ per receive fan."""
    a = [(0, -25.5, 12.5, -3.0, 1.25), (0, -26.0, 13.0, -2.0, 1.0)]
    b = [(0, -27.0, 14.0, 2.0, 0.5), (0, -28.0, 15.0, 3.0, 0.25)]
    path = write_kmall(
        tmp_path / "fans.kmall",
        [mrz(fans=2, fan_index=0, soundings=a), mrz(fans=2, fan_index=1, soundings=b)],
    )
    result = read_kmall(path)
    assert result.number_of_pings == 1
    np.testing.assert_allclose(result.pings[0].depth, [12.5, 13.0, 14.0, 15.0])
    np.testing.assert_allclose(result.pings[0].across_track, [-3.0, -2.0, 2.0, 3.0])


def test_ping_missing_a_fan_is_kept_and_noted(tmp_path: Path) -> None:
    path = write_kmall(
        tmp_path / "partial.kmall",
        [
            mrz(fans=2, fan_index=0, ping_count=1),
            mrz(fans=2, fan_index=0, ping_count=2),
            mrz(fans=2, fan_index=1, ping_count=2),
        ],
    )
    result = read_kmall(path)
    assert result.number_of_pings == 2
    assert any("1 pings missing receive fans" in n for n in result.notes)


def test_dual_swath_gives_two_complete_pings(tmp_path: Path) -> None:
    """EM304 dual swath (real NOAA layout): 2 fans = 2 along-track swaths of 1 fan each."""
    path = write_kmall(
        tmp_path / "dual.kmall",
        [
            mrz(fans=2, fan_index=0, swaths=2, swath_position=0),
            mrz(fans=2, fan_index=1, swaths=2, swath_position=1),
        ],
    )
    result = read_kmall(path)
    assert result.number_of_pings == 2
    assert not any("missing" in n for n in result.notes)
