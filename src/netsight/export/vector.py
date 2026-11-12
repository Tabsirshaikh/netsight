"""GeoJSON, CSV, and KML exports of contact records.

Ellipse coordinates use the specified local metres-per-degree approximation,
not a geodesic projection. Ellipses crossing the antimeridian are split into
RFC 7946 Polygon components for GeoJSON.
"""

import csv
import json
import math
import xml.etree.ElementTree as ET
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from ._common import (
    claim_level,
    ellipse,
    finite_number,
    json_safe,
    position,
    positive_number,
)

Contact = Mapping[str, Any]
PathLike = str | Path
_KML = "http://www.opengis.net/kml/2.2"
_COLUMNS = (
    "contact_id,survey_id,lon,lat,semi_major_m,semi_minor_m,orientation_deg,"
    "p_real,p_lo,p_hi,claim_level,flagged,raw_score,image,x0,y0,x1,y1,"
    "top_class,top_class_prob"
).split(",")


def ellipse_ring(
    lon: float,
    lat: float,
    semi_major_m: float,
    semi_minor_m: float,
    orientation_deg: float,
    n: int = 64,
) -> list[tuple[float, float]]:
    """Return a closed counter-clockwise ellipse in local longitude/latitude."""
    pos = position({"lon": lon, "lat": lat})
    if pos is None:
        raise ValueError("ellipse centre must have a position")
    lon, lat = pos
    major = positive_number(semi_major_m, "semi_major_m")
    minor = positive_number(semi_minor_m, "semi_minor_m")
    if minor > major:
        raise ValueError("semi_minor_m must not exceed semi_major_m")
    angle = math.radians(finite_number(orientation_deg, "orientation_deg"))
    if isinstance(n, bool) or not isinstance(n, int) or n < 3:
        raise ValueError("n must be an integer of at least 3")
    if abs(lat) == 90:
        raise ValueError("local longitude offsets are undefined at the poles")
    scale_x = 111320 * math.cos(math.radians(lat))
    ring = []
    for index in range(n):
        t = 2 * math.pi * index / n
        # The minor axis points left of the major axis, ensuring CCW winding.
        east = major * math.cos(t) * math.sin(angle) - minor * math.sin(t) * math.cos(angle)
        north = major * math.cos(t) * math.cos(angle) + minor * math.sin(t) * math.sin(angle)
        point = (lon + east / scale_x, lat + north / 111320)
        if not -90 <= point[1] <= 90:
            raise ValueError("ellipse extends beyond geographic latitude bounds")
        ring.append(point)
    return [*ring, ring[0]]


def _clip_longitude(
    ring: list[tuple[float, float]], boundary: float, keep_greater: bool
) -> list[tuple[float, float]]:
    """Clip a convex ellipse ring against one longitude boundary."""
    output = []
    previous = ring[-1]
    previous_inside = (previous[0] >= boundary) if keep_greater else (previous[0] <= boundary)
    for current in ring:
        inside = (current[0] >= boundary) if keep_greater else (current[0] <= boundary)
        if inside != previous_inside:
            fraction = (boundary - previous[0]) / (current[0] - previous[0])
            output.append((boundary, previous[1] + fraction * (current[1] - previous[1])))
        if inside:
            output.append(current)
        previous, previous_inside = current, inside
    return output


def _polygon_geometry(ring: list[tuple[float, float]]) -> dict[str, Any]:
    minimum = min(point[0] for point in ring)
    maximum = max(point[0] for point in ring)
    polygons = []
    first = math.floor((minimum + 180) / 360)
    last = math.floor((maximum + 180) / 360)
    for zone in range(first, last + 1):
        clipped = _clip_longitude(ring[:-1], -180 + zone * 360, True)
        if clipped:
            clipped = _clip_longitude(clipped, 180 + zone * 360, False)
        if len(clipped) >= 3:
            points = [[round(x - zone * 360, 7), round(y, 7)] for x, y in clipped]
            polygons.append([[*points, points[0]]])
    if len(polygons) == 1:
        return {"type": "Polygon", "coordinates": polygons[0]}
    return {"type": "MultiPolygon", "coordinates": polygons}


def contacts_geojson(
    contacts: Iterable[Contact], *, research_banner: str, ellipses: bool = False
) -> dict[str, Any]:
    """Build a GeoJSON FeatureCollection, retaining nested contact properties."""
    features = []
    count = withdrawn = 0
    for contact in contacts:
        count += 1
        pos = position(contact)
        if pos is None:
            withdrawn += 1
            continue
        properties = json_safe(dict(contact))
        features.append(
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [round(v, 7) for v in pos]},
                "properties": {**properties, "kind": "contact"},
            }
        )
        parameters = ellipse(contact.get("ellipse95"))
        if ellipses and parameters is not None:
            features.append(
                {
                    "type": "Feature",
                    "geometry": _polygon_geometry(ellipse_ring(*pos, *parameters)),
                    "properties": {**properties, "kind": "ellipse95"},
                }
            )
    return {
        "type": "FeatureCollection",
        "features": features,
        "netsight": {
            "banner": research_banner,
            "positions_withdrawn": withdrawn,
            "n_contacts": count,
        },
    }


def write_geojson(path: PathLike, fc: Mapping[str, Any]) -> Path:
    """Write strict UTF-8 JSON; missing numeric values become null."""
    destination = Path(path)
    destination.write_text(
        json.dumps(json_safe(fc), ensure_ascii=False, allow_nan=False, indent=2),
        encoding="utf-8",
    )
    return destination


def _csv_value(value: Any) -> Any:
    return "" if value is None or json_safe(value) is None else value


def write_csv(path: PathLike, contacts: Iterable[Contact]) -> Path:
    """Write every contact, including those without a position."""
    destination = Path(path)
    with destination.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=_COLUMNS)
        writer.writeheader()
        for contact in contacts:
            row = {key: _csv_value(contact.get(key)) for key in _COLUMNS}
            pos = position(contact)
            row["lon"], row["lat"] = pos if pos is not None else ("", "")
            parameters = ellipse(contact.get("ellipse95"))
            for key, value in zip(
                ("semi_major_m", "semi_minor_m", "orientation_deg"),
                parameters or ("", "", ""),
                strict=True,
            ):
                row[key] = value
            interval = contact.get("p_real_interval")
            if interval is not None:
                if len(interval) != 2:
                    raise ValueError("p_real_interval must contain two values")
                row["p_lo"], row["p_hi"] = map(_csv_value, interval)
            box = contact.get("box_px")
            if box is not None:
                if len(box) != 4:
                    raise ValueError("box_px must contain four values")
                row.update(zip(("x0", "y0", "x1", "y1"), map(_csv_value, box), strict=True))
            probabilities = contact.get("class_probs") or {}
            available = {
                key: finite_number(value, "class probability")
                for key, value in probabilities.items()
                if _csv_value(value) != ""
            }
            if available:
                top = min(available, key=lambda key: (-available[key], key))
                row["top_class"], row["top_class_prob"] = top, available[top]
            writer.writerow(row)
    return destination


def _element(parent: ET.Element, tag: str, text: str | None = None) -> ET.Element:
    child = ET.SubElement(parent, f"{{{_KML}}}{tag}")
    child.text = text
    return child


def contacts_kml(contacts: Iterable[Contact], *, name: str, research_banner: str) -> str:
    """Build namespace-qualified KML with escaped text and contact metadata."""
    root = ET.Element(f"{{{_KML}}}kml")
    document = _element(root, "Document")
    _element(document, "name", name)
    _element(document, "description", research_banner)
    for level, colour in (
        ("calibrated", "ff00ff00"),
        ("indicative", "ff00a5ff"),
        ("withdrawn", "ff888888"),
    ):
        style = _element(document, "Style")
        style.set("id", level)
        _element(_element(style, "IconStyle"), "color", colour)
    for contact in contacts:
        pos = position(contact)
        if pos is None:
            continue
        level = claim_level(contact)
        placemark = _element(document, "Placemark")
        _element(placemark, "name", str(contact["contact_id"]))
        _element(placemark, "styleUrl", f"#{level}")
        extended = _element(placemark, "ExtendedData")
        for key in ("p_real", "claim_level", "flagged", "raw_score"):
            data = _element(extended, "Data")
            data.set("name", key)
            value = _csv_value(contact.get(key))
            _element(data, "value", str(value))
        geometry = _element(placemark, "MultiGeometry")
        _element(_element(geometry, "Point"), "coordinates", f"{pos[0]:.7f},{pos[1]:.7f}")
        parameters = ellipse(contact.get("ellipse95"))
        if parameters is not None:
            boundary = _element(_element(geometry, "Polygon"), "outerBoundaryIs")
            linear_ring = _element(boundary, "LinearRing")
            coordinates = " ".join(
                f"{lon:.7f},{lat:.7f}" for lon, lat in ellipse_ring(*pos, *parameters)
            )
            _element(linear_ring, "coordinates", coordinates)
    return ET.tostring(root, encoding="unicode")


def write_kml(
    path: PathLike, contacts: Iterable[Contact], *, name: str, research_banner: str
) -> Path:
    """Write a UTF-8 KML document."""
    destination = Path(path)
    destination.write_text(
        contacts_kml(contacts, name=name, research_banner=research_banner), encoding="utf-8"
    )
    return destination
