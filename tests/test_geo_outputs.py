import json

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

from netsight.app.geo_outputs import (
    contact_position,
    export_records,
    georeference,
    write_completeness_tiff,
    write_exports,
)


def _tiff_bytes(tmp_path, crs="EPSG:32617", origin=(500000.0, 4000000.0), pixel=1.0):
    path = tmp_path / "m.tif"
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=100,
        width=200,
        count=1,
        dtype="uint8",
        crs=crs,
        transform=from_origin(origin[0], origin[1], pixel, pixel),
    ) as ds:
        ds.write(np.full((100, 200), 80, np.uint8), 1)
    return path.read_bytes()


def test_georeference_and_position(tmp_path):
    g = georeference(_tiff_bytes(tmp_path), "m.tif")
    assert g is not None and g.projected and g.pixel_m == 1.0
    pos = contact_position(g, (0.0, 0.0, 2.0, 2.0))  # centre pixel (1, 1)
    assert pos["map_x"] == pytest.approx(500001.0) and pos["map_y"] == pytest.approx(3999999.0)
    # UTM 17N, easting 500000 is the central meridian -81 deg
    assert pos["lon"] == pytest.approx(-81.0, abs=1e-4)
    assert 36.0 < pos["lat"] < 36.2
    a, b, _ = pos["ellipse95"]
    assert a == b == pytest.approx(np.sqrt((4 + 1 / 12) * 5.991464547107979))


def test_no_georeference_for_plain_images(tmp_path):
    assert georeference(b"not an image", "x.png") is None
    assert georeference(b"garbage", "x.tif") is None


def test_exports_withdraw_unpositioned(tmp_path):
    contacts = [
        {
            "contact_id": "c1",
            "image": "a.tif",
            "box": (0, 0, 2, 2),
            "raw_score": 0.9,
            "probability": 0.8,
            "evidence": {},
            "position": {"lon": -81.0, "lat": 36.1, "ellipse95": [4.0, 4.0, 0.0]},
        },
        {
            "contact_id": "c2",
            "image": "b.png",
            "box": (5, 5, 9, 9),
            "raw_score": 0.7,
            "probability": 0.4,
            "evidence": {},
            "position": None,
        },
    ]
    files = write_exports(
        tmp_path, export_records(contacts, "s", "calibrated"), banner="B", name="n"
    )
    fc = json.loads((tmp_path / files["geojson"]).read_text())
    assert fc["netsight"]["positions_withdrawn"] == 1
    plan = json.loads((tmp_path / files["plan"]).read_text())
    assert [e["contact_id"] for e in plan["entries"]] == ["c1"]
    assert plan["expected_real_total"] == pytest.approx(1.2)
    assert (tmp_path / files["kml"]).read_text().count("<Placemark") == 1


def test_completeness_tiff_on_mosaic_grid(tmp_path):
    g = georeference(_tiff_bytes(tmp_path), "m.tif")
    cells = [
        {"row": r, "col": c, "status": "ok" if r == 0 else "insufficient_trials", "pd_lower": 0.5}
        for r in range(2)
        for c in range(2)
    ]
    out = write_completeness_tiff(tmp_path / "c.tif", cells, g, (100, 200), (2, 2), banner="B")
    with rasterio.open(out) as ds:
        arr = ds.read(1)
        assert ds.transform.a == 100 and ds.transform.c == 500000.0
        assert arr[0, 0] == 0.5 and arr[1, 0] == ds.nodata
