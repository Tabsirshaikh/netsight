"""Hand-checkable vector export and missing-position tests."""

import csv
import json
import math
import xml.etree.ElementTree as ET

import pytest

from netsight.export.vector import (
    contacts_geojson,
    contacts_kml,
    ellipse_ring,
    write_csv,
    write_geojson,
    write_kml,
)


def contact(**changes):
    result = {
        "contact_id": "<&>",
        "survey_id": "s",
        "lon": 20.123456789,
        "lat": 10.0,
        "ellipse95": [10, 5, 0],
        "p_real": 0.75,
        "p_real_interval": [0.5, 0.9],
        "class_probs": {"rock": 0.25, "target": 0.75},
        "claim_level": "calibrated",
        "flagged": False,
        "raw_score": 2,
        "evidence": {"nested": {"value": 4}},
        "image": "image.png",
        "box_px": [1, 2, 3, 4],
    }
    return result | changes


def test_geojson_and_csv(tmp_path):
    contacts = [
        contact(),
        contact(contact_id="missing", lon=None),
        contact(contact_id="nan", lat=float("nan")),
    ]
    fc = contacts_geojson(contacts, research_banner="Research", ellipses=True)
    assert fc["netsight"] == {"banner": "Research", "positions_withdrawn": 2, "n_contacts": 3}
    assert len(fc["features"]) == 2
    point, polygon = fc["features"]
    assert point["geometry"]["coordinates"] == [20.1234568, 10.0]
    assert point["properties"]["kind"] == "contact"
    assert point["properties"]["evidence"] == {"nested": {"value": 4}}
    assert polygon["geometry"]["type"] == "Polygon"
    assert polygon["properties"]["kind"] == "ellipse95"
    path = write_geojson(tmp_path / "contacts.json", fc)
    assert json.loads(path.read_text()) == fc
    path = write_csv(tmp_path / "contacts.csv", contacts)
    with path.open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 3
    assert rows[0]["top_class"] == "target"
    assert rows[0]["top_class_prob"] == "0.75"
    assert rows[0]["p_lo"] == "0.5"
    assert rows[0]["x1"] == "3"
    for row in rows[1:]:
        assert row["lon"] == row["lat"] == ""


def test_ellipse_area_and_orientation():
    ring = ellipse_ring(20, 10, 10, 5, 0)
    assert len(ring) == 65
    assert ring[0] == ring[-1]
    metric = [
        ((lon - 20) * 111320 * math.cos(math.radians(10)), (lat - 10) * 111320) for lon, lat in ring
    ]
    assert metric[0] == pytest.approx((0, 10))
    assert metric[16] == pytest.approx((-5, 0), abs=1e-8)
    area = (
        sum(x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in zip(metric[:-1], metric[1:], strict=True))
        / 2
    )
    assert area == pytest.approx(math.pi * 10 * 5, rel=0.02)
    east = ellipse_ring(20, 10, 10, 5, 90)[0]
    assert (east[0] - 20) * 111320 * math.cos(math.radians(10)) == pytest.approx(10)
    assert east[1] == 10


def test_kml(tmp_path):
    contacts = [contact(), contact(lon=None)]
    text = contacts_kml(contacts, name="Survey", research_banner="Research <only>")
    root = ET.fromstring(text)
    ns = {"k": "http://www.opengis.net/kml/2.2"}
    placemarks = root.findall(".//k:Placemark", ns)
    assert len(placemarks) == 1
    assert placemarks[0].find("k:name", ns).text == "<&>"
    assert placemarks[0].find("k:styleUrl", ns).text == "#calibrated"
    assert len(root.findall(".//k:Style", ns)) == 3
    assert len(root.findall(".//k:MultiGeometry/k:Point", ns)) == 1
    assert len(root.findall(".//k:MultiGeometry/k:Polygon", ns)) == 1
    assert root.find(".//k:description", ns).text == "Research <only>"
    path = write_kml(
        tmp_path / "contacts.kml", contacts, name="Survey", research_banner="Research <only>"
    )
    assert path.read_text() == text


def test_antimeridian_split():
    fc = contacts_geojson([contact(lon=180, lat=0)], research_banner="", ellipses=True)
    geometry = fc["features"][1]["geometry"]
    assert geometry["type"] == "MultiPolygon"
    assert len(geometry["coordinates"]) == 2
    for polygon in geometry["coordinates"]:
        ring = polygon[0]
        assert ring[0] == ring[-1]
        assert all(-180 <= lon <= 180 for lon, _ in ring)
        assert max(lon for lon, _ in ring) - min(lon for lon, _ in ring) < 1


@pytest.mark.parametrize("kwargs", [{"n": 2}, {"semi_minor_m": -1}, {"lat": 90}])
def test_bad_ellipse(kwargs):
    arguments = dict(lon=0, lat=10, semi_major_m=10, semi_minor_m=5, orientation_deg=0)
    with pytest.raises(ValueError):
        ellipse_ring(**(arguments | kwargs))
