import io
from dataclasses import replace

import pytest
from pypdf import PdfReader

from netsight.report import Contact, OperatingSummary, build_pack, render_html, write_pack
from netsight.report.pdf import render_pdf
from netsight.trust.applicability import ClaimDecision
from netsight.trust.wording import DISCLAIMER


def _contact(i: int) -> Contact:
    return Contact(
        contact_id=f"c{i:03d}",
        image="survey.png",
        box=(1.0, 2.0, 30.0, 40.0),
        probability=1 / (i + 2),
        raw_score=0.9 - i * 0.001,
        evidence={"shadow_present": True},
        position=None,
        review=None,
    )


@pytest.fixture
def pack_args() -> dict:
    return {
        "survey_id": "survey-pdf",
        "contacts": [_contact(i) for i in range(3)],
        "claim": ClaimDecision(
            level="indicative",
            reasons=["Pixel geometry differs from the validation surveys."],
            statement="Probabilities are indicative for this survey.",
        ),
        "manifest": {
            "model_id": "research-v04",
            "model_class": "research",
            "label": "RESEARCH MODEL - evaluation only",
            "blocking_datasets": [],
            "datasets": [],
            "manifest_sha256": "a" * 64,
        },
        "operating": OperatingSummary(
            method="label-free count threshold",
            threshold=0.5,
            budget_fa_per_unit=1.0,
            unit="image",
            flagged=3,
            recall_estimate=0.4,
            recall_ci=(0.35, 0.45),
            recall_source="validation surveys",
        ),
        "calibration": {"method": "beta", "fitted_on": "validation"},
        "created": "2026-11-13T00:00:00Z",
        "inputs": {"survey.png": "b" * 64},
        "coverage": {"not_searched_fraction": 0.2, "images": [0.2]},
    }


def _text(pdf: bytes) -> tuple[int, str]:
    reader = PdfReader(io.BytesIO(pdf))
    return len(reader.pages), " ".join(p.extract_text() for p in reader.pages)


def test_pdf_is_one_page_with_disclaimer_banner_and_claim(pack_args):
    pages, text = _text(render_pdf(build_pack(**pack_args)))
    flat = " ".join(text.split())
    assert pages == 1
    assert "Not for navigation" in flat and "does not certify the absence of objects" in flat
    assert "RESEARCH MODEL" in flat and "indicative" in flat and "survey-pdf" in flat
    assert "c000" in flat and "20%" in flat


def test_pdf_stays_one_page_with_many_contacts(pack_args):
    pack_args["contacts"] = [_contact(i) for i in range(250)]
    pack_args["operating"] = replace(pack_args["operating"], flagged=250)
    pages, text = _text(render_pdf(build_pack(**pack_args)))
    assert pages == 1 and "top 10 of 250" in " ".join(text.split())


def test_write_pack_writes_pdf_and_html_has_disclaimer(pack_args, tmp_path):
    pack = build_pack(**pack_args)
    write_pack(pack, tmp_path)
    assert (tmp_path / "evidence_pack.pdf").read_bytes().startswith(b"%PDF")
    from html import escape

    assert escape(DISCLAIMER) in render_html(pack)


def test_navigation_provenance_section(pack_args):
    pack_args["sources"] = [
        {
            "file": "line1.xtf",
            "format": "xtf",
            "n_pings": 30,
            "nav_source_counts": {"sensor": 30},
            "altitude_source_counts": {"recorded": 30},
            "ground_res_m": 0.1,
            "notes": ["rows not resampled to square pixels: implausible stretch"],
        }
    ]
    pack = build_pack(**pack_args)
    html = render_html(pack)
    assert "Navigation provenance" in html and "line1.xtf" in html and "sensor: 30" in html
