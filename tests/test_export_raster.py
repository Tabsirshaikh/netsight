"""Small deterministic raster exports and metric grid placement."""

from dataclasses import dataclass

import numpy as np
import pytest
import rasterio

from netsight.export.raster import grid_from_cells, write_pd_geotiff


@dataclass(frozen=True)
class Cell:
    ix: int
    iy: int
    stratum: str
    pd_lower: float


def test_grid_from_cells():
    cells = [Cell(-1, 0, "a", 0.2), Cell(0, 1, "a", 0.8), Cell(10, 10, "b", 1)]
    grid, x, y = grid_from_cells(cells, "a", cell_size_m=10, origin=(100, 200))
    np.testing.assert_equal(grid, [[np.nan, 0.8], [0.2, np.nan]])
    assert grid.dtype == np.float64
    assert (x, y) == (90, 220)
    with pytest.raises(ValueError, match="stratum"):
        grid_from_cells(cells, "unknown", cell_size_m=10)


def test_geotiff(tmp_path):
    path = write_pd_geotiff(
        tmp_path / "pd.tif",
        np.array([[0.25, np.nan], [0.5, 1.0]]),
        origin_ul_x=100,
        origin_ul_y=220,
        cell_size_m=10,
        crs="EPSG:32631",
        description="Lower detection probability",
        banner="Research only",
    )
    with rasterio.open(path) as dataset:
        assert dataset.shape == (2, 2)
        assert dataset.count == 1
        assert dataset.dtypes == ("float32",)
        assert dataset.transform * (0, 0) == (100, 220)
        assert dataset.transform * (2, 2) == (120, 200)
        assert dataset.nodata == -1
        np.testing.assert_equal(dataset.read(1), [[0.25, -1], [0.5, 1]])
        assert dataset.read(1, masked=True).mask.tolist() == [[False, True], [False, False]]
        assert dataset.tags()["NETSIGHT_BANNER"] == "Research only"
        assert dataset.descriptions == ("Lower detection probability",)
        assert dataset.compression.name == "lzw"
        assert dataset.crs.to_epsg() == 32631


@pytest.mark.parametrize("size", [0, -1, float("nan")])
def test_invalid_cell_size(size):
    with pytest.raises(ValueError, match="cell_size_m"):
        grid_from_cells([Cell(0, 0, "a", 1)], "a", cell_size_m=size)
