import numpy as np
import pytest
import rasterio
from helpers.synth_xtf import write_synthetic_xtf
from rasterio.transform import from_origin

from netsight.core.records import SonarRecord
from netsight.io import UnsupportedFormatError, open_survey
from netsight.io.mosaic import Mosaic, read_mosaic


def write_tiff(path, crs="EPSG:32619", nodata=0):
    data = np.full((10, 20), 120, dtype=np.uint8)
    data[:3, :4] = 0
    with rasterio.open(
        path, "w", driver="GTiff", width=20, height=10, count=1, dtype="uint8",
        crs=crs, transform=from_origin(300000.0, 4500000.0, 1.0, 1.0), nodata=nodata,
    ) as dst:
        dst.write(data, 1)
    return path


def test_reads_mosaic_with_nodata_as_nan(tmp_path):
    m = read_mosaic(write_tiff(tmp_path / "m.tif"))
    assert m.array.shape == (10, 20) and m.array.dtype == np.float32
    assert np.isnan(m.array[0, 0]) and m.array[5, 5] == 120.0
    assert m.pixel_size == (1.0, 1.0) and m.pixel_units == "metre"
    assert m.valid_fraction == pytest.approx(1 - 12 / 200)
    assert m.gain_history_known is False
    assert "unknown gain" in " ".join(m.provenance.notes)


def test_geographic_mosaic_reports_degrees(tmp_path):
    m = read_mosaic(write_tiff(tmp_path / "g.tif", crs="EPSG:4326"))
    assert m.pixel_units == "degree"


def test_open_survey_dispatches(tmp_path):
    assert isinstance(open_survey(write_tiff(tmp_path / "x.tiff")), Mosaic)
    assert isinstance(open_survey(write_synthetic_xtf(tmp_path / "a.xtf", n_pings=2)), SonarRecord)
    with pytest.raises(UnsupportedFormatError):
        open_survey(tmp_path / "file.s7k")


def write_raw(path, data, crs="EPSG:32619", nodata=None):
    if data.ndim == 2:
        data = data[np.newaxis]
    count, height, width = data.shape
    with rasterio.open(
        path, "w", driver="GTiff", width=width, height=height, count=count,
        dtype=str(data.dtype), crs=crs,
        transform=from_origin(300000.0, 4500000.0, 1.0, 1.0), nodata=nodata,
    ) as dst:
        dst.write(data)
    return path


def sentinel_raster():
    data = np.full((10, 20), 120, dtype=np.uint8)
    data[:2, :] = 255  # border-connected no-coverage frame: majority of the border
    data[:, :3] = 255
    data[:, -3:] = 255  # frame is 88 px in total
    data[5, 10] = 255  # isolated interior pixel: real data
    return data


def test_infers_undeclared_border_sentinel(tmp_path):
    m = read_mosaic(write_raw(tmp_path / "s.tif", sentinel_raster()))
    assert np.isnan(m.array[:, :3]).all() and np.isnan(m.array[:2]).all()
    assert m.array[5, 10] == 255.0
    assert m.valid_fraction == pytest.approx(1 - 88 / 200)
    assert any("inferred 255" in n and "(88 pixels)" in n for n in m.provenance.notes)
    assert m.extra["nodata_source"] == "inferred"
    assert m.extra["band"] == 1 and m.extra["band_count"] == 1


def test_no_qualifying_sentinel_keeps_all_valid(tmp_path):
    data = np.full((10, 20), 120, dtype=np.uint8)
    data[5, 10] = 255
    m = read_mosaic(write_raw(tmp_path / "n.tif", data))
    assert m.valid_fraction == 1.0
    assert any("no sentinel inferred" in n for n in m.provenance.notes)
    assert m.extra["nodata_source"] == "none"


def test_explicit_nodata_overrides_declared(tmp_path):
    path = write_tiff(tmp_path / "o.tif", nodata=0)  # file declares 0, 12 px of 0
    m = read_mosaic(path, nodata=120)
    assert np.isnan(m.array[5, 5]) and m.array[0, 0] == 0.0
    assert m.valid_fraction == pytest.approx(12 / 200)
    assert m.extra["nodata_source"] == "override"
    assert read_mosaic(path).extra["nodata_source"] == "declared"


def test_mosaic_without_crs_notes_it(tmp_path):
    m = read_mosaic(write_raw(tmp_path / "c.tif", sentinel_raster(), crs=None))
    assert m.crs_wkt is None
    assert "mosaic has no CRS" in m.provenance.notes


def test_multiband_mosaic_records_band_count(tmp_path):
    data = np.stack([np.full((10, 20), 100, np.uint8), np.full((10, 20), 50, np.uint8)])
    m = read_mosaic(write_raw(tmp_path / "b.tif", data), band=2)
    assert m.extra["band"] == 2 and m.extra["band_count"] == 2
    assert m.array[0, 0] == 50.0
    assert any("2 bands" in n and "band 2" in n for n in m.provenance.notes)
