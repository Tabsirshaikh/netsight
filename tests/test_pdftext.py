from helpers.tiny_pdf import write_text_pdf

from netsight.data.noaa_dr import dr_summary, parse_contact_tables
from netsight.data.pdftext import extract_pages


def test_extract_pages_returns_one_string_per_page(tmp_path):
    row = "227-034244S H33-I-E 12.133 28-48-19.481 91-16-40.857 Disproved"
    pdf = write_text_pdf(tmp_path / "dr.pdf", [["Descriptive Report H99999"], [row]])
    pages = extract_pages(pdf)
    assert len(pages) == 2
    assert "H99999" in pages[0]
    rows = parse_contact_tables(pages, "H99999")
    assert [r.contact_id for r in rows] == ["227-034244S"] and rows[0].page == 2


def test_dr_summary_counts_and_flags():
    pages = [
        "Number of items investigated 4\nKlein 5000 side scan sonar\n200% side scan sonar coverage",
        "Separates V Side Scan Contact Listing and Images of Significant Contacts",
        "227-034244S H33-I-E 12.133 28-48-19.481 91-16-40.857 Disproved",
    ]
    s = dr_summary(pages, "H99999")
    assert s["survey_id"] == "H99999"
    assert s["items_investigated"] == 4
    assert s["contact_rows"] == 1
    assert s["contact_list_in_separate"] is True
    assert s["sss_coverage_percent"] == 200
    assert s["mentions_side_scan"] is True


def test_dr_summary_without_tables():
    s = dr_summary(["Nothing about sonar here."], "H1")
    assert s["items_investigated"] is None and s["contact_rows"] == 0
    assert s["sss_coverage_percent"] is None and s["mentions_side_scan"] is False
