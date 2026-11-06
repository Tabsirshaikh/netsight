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
