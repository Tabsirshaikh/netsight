import numpy as np
import pytest
from helpers.synth_xtf import write_synthetic_xtf

from netsight.app.raw_ingest import RAW_EXTENSIONS, ingest_raw, locate_box


def _xtf(tmp_path, **kw):
    return write_synthetic_xtf(tmp_path / "s.xtf", n_samples=500, **kw).read_bytes()


def test_raw_file_becomes_port_stbd_waterfall_with_provenance(tmp_path):
    raw = ingest_raw(_xtf(tmp_path, n_pings=40), "survey.xtf")
    assert len(raw.chunks) == 1
    chunk = raw.chunks[0]
    n_bins = raw.swath.port.shape[1]
    assert chunk.image.dtype == np.uint8 and chunk.image.shape == (40, 2 * n_bins)
    assert chunk.not_searched.shape == chunk.image.shape
    # water column either side of nadir (middle of the waterfall) is not searched
    assert chunk.not_searched[:, n_bins - 2 : n_bins + 2].all()
    s = raw.summary
    assert s["format"] == "xtf" and s["n_pings"] == 40
    assert s["nav_source_counts"] == {"sensor": 40}
    assert s["ground_res_m"] == pytest.approx(0.1)
    assert any("not resampled" in n for n in s["notes"])  # the synthetic vessel never moves


def test_long_files_are_split_into_chunks(tmp_path):
    raw = ingest_raw(_xtf(tmp_path, n_pings=40), "survey.xtf", max_rows=16)
    assert [c.image.shape[0] for c in raw.chunks] == [16, 16, 8]
    assert len({c.name for c in raw.chunks}) == 3
    with pytest.raises(ValueError, match="too long"):
        ingest_raw(_xtf(tmp_path, n_pings=40), "survey.xtf", max_rows=4, max_chunks=5)


def test_contact_position_from_ping_navigation(tmp_path):
    raw = ingest_raw(_xtf(tmp_path, n_pings=20), "survey.xtf")
    n_bins = raw.swath.port.shape[1]
    stbd = locate_box(raw, 0, (n_bins + 100, 5, n_bins + 110, 9))  # ~10.5 m to starboard
    port = locate_box(raw, 0, (n_bins - 110, 5, n_bins - 100, 9))
    assert stbd["side"] == "stbd" and port["side"] == "port"
    assert stbd["ground_range_m"] == pytest.approx(10.5, abs=0.11)
    assert np.isfinite([stbd["lon"], stbd["lat"]]).all() and stbd["ellipse95"] is not None
    assert stbd["lon"] != port["lon"] or stbd["lat"] != port["lat"]


def test_extensions():
    assert RAW_EXTENSIONS == {".xtf", ".jsf"}


def test_absent_side_is_left_out_and_positions_still_use_the_right_side(tmp_path):
    data = write_synthetic_xtf(
        tmp_path / "p.xtf", n_pings=20, n_samples=500, channel_types=(2,)
    ).read_bytes()  # starboard only
    raw = ingest_raw(data, "stbd_only.xtf")
    n_bins = raw.swath.stbd.shape[1]
    assert raw.chunks[0].image.shape[1] == n_bins and raw.port_width == 0
    assert raw.summary["absent_sides"] == ["port"] and raw.summary["not_searched_fraction"] < 0.5
    pos = locate_box(raw, 0, (100, 5, 110, 9))
    assert pos["side"] == "stbd" and pos["ground_range_m"] == pytest.approx(10.5, abs=0.11)
