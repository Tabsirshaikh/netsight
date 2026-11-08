"""Tests for the offline NOAA review workflow."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from typing import Any

from PIL import Image

from netsight.datasets.noaa_chips import _safe_component
from netsight.datasets.review_page import apply_review, build_review_page


class ReviewPageTests(unittest.TestCase):
    """Exercise page embedding, review export, and validation."""

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.root = self.base / "chips"
        self.ids = [
            ("H12330", "contact/one"),
            ("H12330", "contact-<two>&"),
            ("H45678", "contact-three"),
            ("H45678", "contact-nodata"),
        ]
        surveys: dict[str, list[dict[str, Any]]] = {}
        for index, (survey, contact) in enumerate(self.ids):
            record = {
                "survey_id": survey,
                "contact_id": contact,
                "is_real": index == 0,
                "kind": "debris",
                "box_px": [32, 64, 96, 128],
                "centre_px": [64, 96],
                "metres_per_px": 0.5,
                "window": [0, 0, 256, 256],
                "status": "nodata" if index == 3 else "ok",
                "valid_fraction": 0.0 if index == 3 else 1.0,
                "provenance": {"source": "test"},
                "label_status": "unreviewed",
            }
            surveys.setdefault(survey, []).append(record)
            directory = self.root / survey
            directory.mkdir(parents=True, exist_ok=True)
            if record["status"] == "ok":
                Image.new("L", (256, 256), color=100).save(
                    directory / f"{survey}_{_safe_component(contact)}.png"
                )
        for survey, records in surveys.items():
            (self.root / survey / "manifest.json").write_text(json.dumps(records), encoding="utf-8")

    def write_review(self, entries: list[dict[str, Any]]) -> Path:
        """Write a versioned review fixture."""
        path = self.base / "review.json"
        path.write_text(json.dumps({"version": 1, "items": entries}), encoding="utf-8")
        return path

    def entries(self) -> list[dict[str, Any]]:
        """Make one entry for each supported decision."""
        return [
            {
                "survey_id": survey,
                "contact_id": contact,
                "decision": decision,
                # Keep must use the manifest box rather than this supplied box.
                "box_px": [-16, 32, 128, 288] if decision == "move" else [0, 0, 2, 2],
                "reviewed_at": "2026-01-01T00:00:00.000Z",
            }
            for (survey, contact), decision in zip(
                self.ids, ("keep", "move", "reject", "unsure"), strict=True
            )
        ]

    def test_build_embeds_only_ok_chips_and_escapes_data(self) -> None:
        page = self.base / "review.html"
        self.assertEqual(build_review_page(self.root, page), 3)
        html = page.read_text(encoding="utf-8")
        self.assertEqual(html.count("data:image/png;base64,"), 3)
        self.assertNotIn("http://", html)
        self.assertNotIn("https://", html)
        marker = '<script type="application/json" id="review-data">'
        before, remainder = html.split(marker, 1)
        block, after = remainder.split("</script>", 1)
        payload = json.loads(block)
        self.assertEqual(len(payload["items"]), 3)
        for _, contact in self.ids[:3]:
            self.assertNotIn(contact, before + after)
        self.assertNotIn(self.ids[3][1], html)
        self.assertNotIn("<two>", block)
        self.assertIn(r"\u003ctwo\u003e\u0026", block)
        self.assertEqual(payload["items"][0]["contact_id"], "contact/one")

    def test_apply_exports_boxes_images_and_manifest(self) -> None:
        out = self.base / "export"
        counts = apply_review(self.root, self.write_review(self.entries()), out)
        self.assertEqual(counts, {"keep": 1, "move": 1, "reject": 1, "unsure": 1, "undecided": 0})
        self.assertEqual(len(list(out.glob("*.txt"))), 2)
        self.assertEqual(len(list(out.glob("*.png"))), 2)
        expected = [
            [0.25, 0.375, 0.25, 0.25],
            [0.25, 0.5625, 0.5, 0.875],
        ]
        for (survey, contact), numbers in zip(self.ids[:2], expected, strict=True):
            stem = f"{survey}_{_safe_component(contact)}"
            fields = (out / f"{stem}.txt").read_text(encoding="utf-8").split()
            self.assertEqual(fields[0], "0")
            for actual, wanted in zip(map(float, fields[1:]), numbers, strict=True):
                self.assertAlmostEqual(actual, wanted)
            self.assertEqual(
                (out / f"{stem}.png").read_bytes(),
                (self.root / survey / f"{stem}.png").read_bytes(),
            )
        manifest = json.loads((out / "reviewed_manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(len(manifest), 4)
        self.assertEqual([item["decision"] for item in manifest], list(counts)[:4])
        for item in manifest[:2]:
            self.assertEqual(item["label_status"], "reviewed by a person")
        self.assertEqual(manifest[1]["box_px"], [0, 32, 128, 256])
        self.assertIsNone(manifest[2]["box_px"])

    def test_unknown_ids_raise_before_export(self) -> None:
        entries = self.entries()
        entries[0]["contact_id"] = "unknown"
        out = self.base / "invalid"
        with self.assertRaisesRegex(ValueError, "Unknown survey/contact"):
            apply_review(self.root, self.write_review(entries), out)
        self.assertFalse(out.exists())

    def test_tiny_clipped_box_is_skipped_and_stale_export_removed(self) -> None:
        out = self.base / "export"
        entries = self.entries()
        apply_review(self.root, self.write_review(entries), out)
        # The drawn box is large before clipping but only one pixel wide afterward.
        entries[1]["box_px"] = [-30, 10, 1, 50]
        counts = apply_review(self.root, self.write_review(entries), out)
        self.assertEqual(counts["move"], 1)
        self.assertEqual(len(list(out.glob("*.txt"))), 1)
        self.assertEqual(len(list(out.glob("*.png"))), 1)

    def test_missing_decisions_remain_undecided(self) -> None:
        out = self.base / "partial"
        counts = apply_review(self.root, self.write_review(self.entries()[:1]), out)
        self.assertEqual(counts["keep"], 1)
        self.assertEqual(counts["undecided"], 3)
        manifest = json.loads((out / "reviewed_manifest.json").read_text(encoding="utf-8"))
        self.assertTrue(all(item["decision"] is None for item in manifest[1:]))


if __name__ == "__main__":
    unittest.main()
