from pathlib import Path

import pytest

from netsight.data.noaa_dr import (
    classify_disposition,
    dms_to_degrees,
    parse_contact_tables,
    write_contacts_csv,
)

FIXTURE = Path(__file__).parent / "fixtures" / "noaa" / "H12333_dr_excerpt.txt"


@pytest.fixture(scope="module")
def contacts():
    return parse_contact_tables([FIXTURE.read_text(encoding="utf-8")], "H12333")


def by_id(rows, contact_id):
    return [r for r in rows if r.contact_id == contact_id]


def test_dms_to_degrees():
    assert dms_to_degrees("28-48-19.481") == pytest.approx(28 + 48 / 60 + 19.481 / 3600)
    assert dms_to_degrees("n/a") is None
    assert dms_to_degrees("garbage") is None


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("DTON1", ("dton", True)),
        ("Confirmed as insignificant", ("real_insignificant", True)),
        ("Disproved", ("disproved", False)),
        ("Depression", ("seabed_feature", False)),
        ("Evident in SSS; no height off bottom in MB", ("no_height", None)),
        ("Exposed Pipeline - charted", ("real_known_feature", True)),
        ("Obstruction currently uncharted.", ("real_obstruction", True)),
        ("something new", ("unknown", None)),
    ],
)
def test_classify_disposition(text, expected):
    assert classify_disposition(text) == expected


def test_parses_all_table_rows_from_real_report_excerpt(contacts):
    ids = [r.contact_id for r in contacts]
    for expected in [
        "227-010243S", "226-174911S", "225-105617P", "225-033037P", "227-034244S",
        "227-085156S", "231-184726S", "224-150725P", "228-233126P", "224-043515P",
        "227-034233S",
    ]:
        assert expected in ids
    assert all(r.survey_id == "H12333" for r in contacts)


def test_investigated_contact_with_position(contacts):
    (row,) = by_id(contacts, "227-034244S")
    assert row.investigation == "H33-I-E"
    assert row.least_depth_m == pytest.approx(12.133)
    assert row.lat == pytest.approx(28 + 48 / 60 + 19.481 / 3600)
    assert row.lon == pytest.approx(-(91 + 16 / 60 + 40.857 / 3600))
    assert row.hemisphere_assumed is True  # Table 9 gives no N/W
    assert (row.disposition, row.is_real_object) == ("real_insignificant", True)
    assert row.ground_truth == "multibeam_developed"


def test_disproved_and_missing_values(contacts):
    (row,) = by_id(contacts, "226-174911S")
    assert row.least_depth_m is None and row.lat is None and row.lon is None
    assert (row.disposition, row.is_real_object) == ("disproved", False)
    assert row.ground_truth == "expert_disposition"


def test_multi_line_remarks_are_joined(contacts):
    (row,) = by_id(contacts, "225-033037P")
    assert row.remarks == "Evident in SSS; no height off bottom in MB"
    assert (row.disposition, row.is_real_object) == ("no_height", None)


def test_table_caption_classifies_rows_without_remarks(contacts):
    (row,) = by_id(contacts, "228-233126P")
    assert row.investigation is None
    assert row.lat == pytest.approx(28 + 44 / 60 + 51.261 / 3600)
    assert row.lon == pytest.approx(-(91 + 12 / 60 + 8.347 / 3600))
    assert row.hemisphere_assumed is False  # explicit N / W in the row
    assert (row.disposition, row.is_real_object) == ("real_obstruction", True)
    assert "pipeline" in row.table_caption.lower()


def test_depth_with_unit_suffix(contacts):
    (row,) = by_id(contacts, "224-043515P")
    assert row.least_depth_m == pytest.approx(15.880)
    assert row.disposition == "real_obstruction"


def test_dton_and_prose_mentions_are_not_rows(contacts):
    (row,) = by_id(contacts, "224-150725P")
    assert (row.disposition, row.is_real_object) == ("dton", True)
    # contacts only mentioned in prose ("associated with contact 229-043001P") are not table rows
    assert by_id(contacts, "229-043001P") == []


def test_page_numbers_follow_input_pages():
    rows = parse_contact_tables(
        ["intro text", "227-034244S H33-I-E 12.133 28-48-19.481 91-16-40.857 Disproved"], "HX"
    )
    assert rows[0].page == 2


def test_write_contacts_csv(tmp_path, contacts):
    out = write_contacts_csv(contacts, tmp_path / "c.csv")
    lines = out.read_text(encoding="utf-8").splitlines()
    assert lines[0].startswith("survey_id,contact_id,investigation")
    assert len(lines) == len(contacts) + 1
