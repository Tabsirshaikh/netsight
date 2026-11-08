"""Synthetic georeferencing, candidate-box, and export tests."""

from __future__ import annotations

import csv
import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from typing import cast

import numpy as np
import rasterio
from PIL import Image
from pyproj import Transformer
from rasterio.transform import from_origin

from netsight.datasets.noaa_chips import (
    LABEL_STATUS,
    Contact,
    load_contacts,
    lonlat_to_pixel,
    make_chips,
    write_chips,
)
from netsight.io.mosaic import Mosaic, read_mosaic


class NoaaChipsTests(unittest.TestCase):
    """Exercise chip creation using a small UTM survey."""

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.transform = from_origin(500000, 4500000, 1, 1)
        self.to_lonlat = Transformer.from_crs(32615, 4326, always_xy=True)
        rows, cols = np.indices((400, 500))
        data = (10 + (rows + cols) % 17).astype(np.float32)
        data[197:203, 247:253] = 250
        data[197:203, 5:11] = 250
        data[:140, :140] = np.nan
        self.path = self.root / "mosaic.tif"
        with rasterio.open(
            self.path,
            "w",
            driver="GTiff",
            width=500,
            height=400,
            count=1,
            dtype="float32",
            crs="EPSG:32615",
            transform=self.transform,
            nodata=np.nan,
        ) as dataset:
            dataset.write(data, 1)
        self.mosaic = read_mosaic(self.path)
        self.contact = self.at_pixel("blob", 250.0, 200.0)
        self.csv_path = self.root / "contacts.csv"
        self.write_csv(self.csv_path, [self.contact])

    def at_pixel(
        self,
        contact_id: str,
        col: float,
        row: float,
        is_real: bool | None = True,
    ) -> Contact:
        """Create a contact at continuous corner-based coordinates."""
        x, y = self.transform * (col, row)
        lon, lat = self.to_lonlat.transform(x, y)
        return Contact("H12330", contact_id, lat, lon, is_real, "", "synthetic")

    def write_csv(self, path: Path, contacts: list[Contact], *, features: bool = False) -> None:
        """Write either NOAA contact table schema."""
        id_column = "item_no" if features else "contact_id"
        with path.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(
                stream,
                fieldnames=["survey_id", id_column, "lat", "lon", "is_real_object"],
            )
            writer.writeheader()
            for contact in contacts:
                writer.writerow(
                    {
                        "survey_id": contact.survey_id,
                        id_column: contact.contact_id,
                        "lat": contact.lat,
                        "lon": contact.lon,
                        "is_real_object": ("" if contact.is_real is None else str(contact.is_real)),
                    }
                )

    def test_round_trip_pixel_centre(self) -> None:
        contact = self.at_pixel("centre", 250.5, 200.5)
        col, row = lonlat_to_pixel(self.mosaic, contact.lon, contact.lat)
        self.assertAlmostEqual(col, 250.5, delta=0.1)
        self.assertAlmostEqual(row, 200.5, delta=0.1)

    def test_blob_and_box(self) -> None:
        contacts = load_contacts([self.csv_path], "H12330")
        record = make_chips(self.mosaic, contacts)[0]
        self.assertEqual(record.status, "ok")
        self.assertEqual(record.chip.shape, (256, 256))
        self.assertEqual(record.chip.dtype, np.uint8)
        x0, y0, x1, y1 = record.box_px
        self.assertAlmostEqual(x1 - x0, 10)
        self.assertAlmostEqual(y1 - y0, 10)
        cx, cy = record.centre_px
        self.assertAlmostEqual((x0 + x1) / 2, cx)
        self.assertAlmostEqual((y0 + y1) / 2, cy)
        self.assertEqual(record.chip[int(cy), int(cx)], 255)
        # 1st-99th percentile scaling saturates the brightest ~1% of the mosaic, not only the blob
        blob = record.chip[int(cy) - 2 : int(cy) + 3, int(cx) - 2 : int(cx) + 3]
        self.assertTrue(np.all(blob == 255))
        self.assertLess(np.median(record.chip), 255)

    def test_edge_window_shift(self) -> None:
        contact = self.at_pixel("edge", 8.0, 200.0)
        record = make_chips(self.mosaic, [contact], chip_px=64)[0]
        self.assertEqual(record.status, "ok")
        self.assertEqual(record.window[1], 0)
        self.assertAlmostEqual(record.centre_px[0], 8)
        x0, y0, x1, y1 = record.box_px
        self.assertAlmostEqual(x1 - x0, 10)
        self.assertAlmostEqual(y1 - y0, 10)
        self.assertEqual(record.chip[int((y0 + y1) / 2), int((x0 + x1) / 2)], 255)

    def test_outside_and_nodata(self) -> None:
        contacts = [
            self.at_pixel("outside", -10, 200),
            self.at_pixel("nan", 40, 40),
        ]
        outside, nodata = make_chips(self.mosaic, contacts, chip_px=64)
        self.assertEqual(outside.status, "outside")
        self.assertEqual(nodata.status, "nodata")
        self.assertEqual(nodata.valid_fraction, 0)
        self.assertEqual(nodata.chip.size, 0)
        manifest = write_chips([outside, nodata], self.root / "skipped")
        entries = json.loads(manifest.read_text(encoding="utf-8"))
        self.assertEqual([entry["status"] for entry in entries], ["outside", "nodata"])
        self.assertEqual(list(manifest.parent.glob("*.png")), [])

    def test_dedupe_and_prefer_real_across_tables(self) -> None:
        first = replace(self.contact, is_real=False)
        second = self.at_pixel("feature", 252, 200, True)
        third = self.at_pixel("later", 253, 200, True)
        self.write_csv(self.csv_path, [first])
        features = self.root / "features.csv"
        self.write_csv(features, [second, third], features=True)
        contacts = load_contacts([self.csv_path, features], "H12330")
        self.assertEqual(len(contacts), 1)
        self.assertEqual(contacts[0].contact_id, "feature")
        self.assertIs(contacts[0].is_real, True)
        self.assertEqual(contacts[0].source_file, str(features))
        self.assertEqual(load_contacts([features], "OTHER"), [])

    def test_write_and_decode_yolo(self) -> None:
        record = make_chips(self.mosaic, [self.contact])[0]
        manifest_path = write_chips([record], self.root / "output")
        entries = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(len(entries), 1)
        entry = entries[0]
        self.assertEqual(entry["label_status"], LABEL_STATUS)
        self.assertNotIn("chip", entry)
        png = manifest_path.parent / "H12330_blob.png"
        label = manifest_path.parent / "H12330_blob.txt"
        self.assertTrue(png.exists())
        self.assertTrue(label.exists())
        with Image.open(png) as image:
            np.testing.assert_array_equal(np.asarray(image), record.chip)
        category, cx, cy, width, height = label.read_text(encoding="utf-8").split()
        self.assertEqual(category, "0")
        cx, cy, width, height = map(float, (cx, cy, width, height))
        decoded = (
            (cx - width / 2) * 256,
            (cy - height / 2) * 256,
            (cx + width / 2) * 256,
            (cy + height / 2) * 256,
        )
        np.testing.assert_allclose(decoded, record.box_px, atol=1e-7)

    def test_missing_crs(self) -> None:
        mosaic = cast(Mosaic, SimpleNamespace(crs_wkt=None))
        with self.assertRaises(ValueError):
            lonlat_to_pixel(mosaic, self.contact.lon, self.contact.lat)


if __name__ == "__main__":
    unittest.main()
