"""Pydro Feature Report items (AWOIS / DTON / new features) from real CC0 NOAA DR excerpts."""

import csv
import re
from pathlib import Path

import pytest

from netsight.data.noaa_features import (
    FeatureItem,
    classify_feature,
    parse_feature_items,
    write_features_csv,
)

FIXTURE = Path(__file__).parent / "fixtures" / "noaa" / "feature_items_excerpt.txt"
PAGE = re.compile(r"^<<<PAGE (H\d{5}) (\d+)>>>$", re.M)


def _pages_by_survey() -> dict[str, list[str]]:
    text = FIXTURE.read_text(encoding="utf-8")
    marks = list(PAGE.finditer(text))
    out: dict[str, list[str]] = {}
    for i, m in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(text)
        out.setdefault(m.group(1), []).append(text[m.end() : end])
    return out


@pytest.fixture(scope="module")
def items() -> dict[str, list[FeatureItem]]:
    return {sid: parse_feature_items(pages, sid) for sid, pages in _pages_by_survey().items()}


def _one(items, survey, name_part) -> FeatureItem:
    found = [it for it in items[survey] if name_part in it.name]
    assert len(found) == 1, [it.name for it in items[survey]]
    return found[0]


def test_verified_rock_with_position_depth_and_class(items):
    it = _one(items, "H12411", "AWOIS 6804")
    assert it.disposition == "verified" and it.is_real_object is True
    assert it.s57_class == "UWTROC" and it.item_kind == "awois"
    assert it.least_depth_m == pytest.approx(10.33)
    assert it.lat == pytest.approx(41 + 1 / 60 + 45.8 / 3600)
    assert it.lon == pytest.approx(-(73 + 27 / 60 + 12.9 / 3600))
    assert it.mentions_mbes and it.ground_truth == "multibeam_developed"


def test_history_notes_do_not_drive_the_disposition(items):
    it = _one(items, "H12411", "AWOIS 6804")
    assert "SIGNIFICANT CONTACT" not in (it.remarks + it.recommendation + it.office_notes)


def test_disproved_by_side_scan(items):
    it = _one(items, "H12333", "12791")
    assert it.disposition == "disproved" and it.is_real_object is False
    assert it.mentions_sss and it.s57_class == "$CSYMB"


def test_disproved_by_multibeam(items):
    it = _one(items, "H12411", "AWOIS 6441")
    assert it.disposition == "disproved" and it.is_real_object is False


def test_office_overrides_field_deletion(items):
    it = _one(items, "H12357", "AWOIS 14921")
    assert it.office_overrode is True
    assert it.disposition == "verified" and it.is_real_object is True


@pytest.mark.parametrize(
    ("survey", "name"),
    [("H12357", "AWOIS 3157"), ("H12357", "AWOIS 6922"), ("H12417", "AWOIS 11825"),
     ("H12408", "AWOIS#14999")],
)
def test_not_found_items_are_disproved(items, survey, name):
    it = _one(items, survey, name)
    assert it.disposition == "disproved" and it.is_real_object is False
    assert it.office_overrode is False


def test_retained_without_new_evidence_is_unknown(items):
    it = _one(items, "H12357", "AWOIS 14927")
    assert it.disposition == "retained_unverified" and it.is_real_object is None


def test_sandwave_is_seabed_not_object(items):
    it = _one(items, "H12381", "0000012872")
    assert it.disposition == "reclassified_seabed" and it.is_real_object is False
    assert it.item_kind == "dton" and it.s57_class == "SNDWAV"


def test_not_a_rock_is_seabed_not_object(items):
    it = _one(items, "H12381", "0000013007")
    assert it.disposition == "reclassified_seabed" and it.is_real_object is False


def test_new_dton_rock_found_by_mbes(items):
    it = _one(items, "H12417", "8ft rock")
    assert it.disposition == "verified" and it.item_kind == "dton"
    assert it.least_depth_m == pytest.approx(2.64)


def test_update_least_depth_counts_as_verified(items):
    it = _one(items, "H12408", "AWOIS#11233")
    assert it.disposition == "verified" and it.s57_class == "WRECKS"


def test_found_wreck_despite_delete_wording(items):
    it = _one(items, "H12309", "0001375462")
    assert it.disposition == "verified" and it.is_real_object is True
    assert it.mentions_sss and it.mentions_mbes
    # survey (found) position, not the older charted search position 36-58-34.5
    assert it.lat == pytest.approx(36 + 58 / 60 + 33.2 / 3600)


def test_fish_stakes_observed(items):
    # two features share the name "AWOIS 6477" (items 1.9 and 1.10); 1.9 is the fish stakes
    it = next(i for i in items["H12411"] if i.item_no == "1.9")
    assert it.s57_class == "FSHFAC" and it.is_real_object is True


def test_every_item_has_a_position(items):
    for survey_items in items.values():
        for it in survey_items:
            assert it.lat is not None and it.lon is not None


def test_item_without_position_is_skipped():
    assert parse_feature_items(["1.1)  Something\nRemarks:\nnothing here"], "H1") == []


def test_duplicate_reports_of_one_item_are_merged():
    body = (
        "{n})  DTON {n}\n DANGER TO NAVIGATION\nSurvey Position:  30° 09' 14.9\" N,"
        " 085° 40' 08.2\" W\nLeast Depth:  3.42 m\nRemarks:\n{r}\n"
    )
    pages = [body.format(n="1.1", r="Rock found by MBES."), body.format(n="2.1", r="[None]")]
    out = parse_feature_items(pages, "H2")
    assert len(out) == 1 and out[0].disposition == "verified"


@pytest.mark.parametrize(
    ("office", "rec", "remarks", "expected"),
    [
        ("Concur", "Delete wreck.", "No evidence of wreck found in 200% SSS.", "disproved"),
        ("Concur", "Delete wreck.", "", "deleted"),
        ("", "Chart rock.", "", "verified"),
        ("", "[None]", "[None]", "unknown"),
        ("Do not concur. Feature is real.", "Delete obstruction.", "", "verified"),
    ],
)
def test_classify_feature_rules(office, rec, remarks, expected):
    disposition, _, _ = classify_feature(remarks, rec, office, s57_class=None, least_depth_m=None)
    assert disposition == expected


def test_write_features_csv(tmp_path, items):
    path = write_features_csv(items["H12411"], tmp_path / "f.csv")
    rows = list(csv.DictReader(open(path, encoding="utf-8")))
    assert len(rows) == len(items["H12411"]) and rows[0]["source"] == "feature_report"


# Cases found by spot-checking all 29 downloaded surveys (texts quoted from the CC0 DRs).
@pytest.mark.parametrize(
    ("office", "rec", "remarks", "s57", "expected", "real"),
    [
        # H12357 1.17: an object is likely there; "disprove" is negated
        ("Concur", "Retain Pile",
         "Review of data indicates an object at this location. Shadow analysis indicates 0.6m "
         "height off the bottom. Survey data is inadequate to disprove this item.",
         None, "inconclusive", None),
        # H12414 1.2
        ("SAR: AWOIS 11824 search area was incomplete. Charted feature is not considered as "
         "disproved although no evidence of shellfish racks were observed.",
         "Retain as charted.", "", "MARCUL", "inconclusive", None),
        # H12411 1.4: office decides before the field remark's "no evidence of an obstruction"
        ("SAR: Rock verified with object detection multibeam.", "Chart rock.",
         "Rock was found, but no evidence of an obstruction was found.", "UWTROC",
         "verified", True),
        # H12357 1.16
        ("Concur. Delete submeged pile.", "Recommend removal of Awois #3164.",
         "Multiple rock contacts seen in radius, but no significant contact detected within "
         "AWOIS radius in SSS data.", None, "disproved", False),
        # H12315 1.7
        ("Confirm field recommendation, feature Wreck is verified as not present by 200% SSS.",
         "Delete disproved Wreck PA", "", "$CSYMB", "disproved", False),
        # H12408 2.6: a mooring buoy is a man-made object, not seabed
        ("Retain charted mooring buoy.", "Retain mooring buoy", "US Navy mooring buoy",
         "MORFAC", "retained_unverified", None),
        # H12348 3.1
        ("", "Reposition AWOIS 54051 as surveyed.", "AWOIS 54051. approx ext MLLW", "$CSYMB",
         "verified", True),
        # a bare deletion without stated evidence is not proof of absence
        ("Concur", "Delete wreck.", "", None, "deleted", None),
    ],
)
def test_classify_feature_spot_check_cases(office, rec, remarks, s57, expected, real):
    disposition, is_real, _ = classify_feature(
        remarks, rec, office, s57_class=s57, least_depth_m=None
    )
    assert (disposition, is_real) == (expected, real)


def test_found_seabed_feature_is_still_seabed():
    # H12318 1.1: a real shoal, but seabed relief rather than a discrete object
    remarks = "A 2 3/4 fathom sounding was found adjacent to a 15 fathom charted sounding."
    disposition, is_real, _ = classify_feature(
        remarks, "", "", s57_class="SOUNDG", least_depth_m=5.06
    )
    assert (disposition, is_real) == ("reclassified_seabed", False)


@pytest.mark.parametrize("minute_mark", ["'", "’", "′", "�"])
def test_position_accepts_typographic_minute_marks(minute_mark):
    m = minute_mark
    page = (
        f"1.1)  DTON 1\nSurvey Position:  30° 09{m} 14.9\" N, 085° 40{m} 08.2\" W\n"
        "Least Depth:  3.42 m\nRemarks:\nRock found by MBES.\n"
    )
    (item,) = parse_feature_items([page], "H3")
    assert item.lon == pytest.approx(-(85 + 40 / 60 + 8.2 / 3600))
