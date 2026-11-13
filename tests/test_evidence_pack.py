"""Tests for deterministic evidence packs and their trust restrictions."""

import json
from dataclasses import replace
from hashlib import sha256
from pathlib import Path

import pytest

from netsight.report import Contact, OperatingSummary, build_pack, render_html, write_pack
from netsight.trust.applicability import ClaimDecision
from netsight.trust.provenance import Ledger


@pytest.fixture
def contact() -> Contact:
    return Contact(
        contact_id="c1",
        image="sonar.png",
        box=(1.0, 2.0, 30.0, 40.0),
        raw_score=0.8,
        probability=0.7,
        evidence={"shadow_present": False, "height_m": None, "line_length_px": 12.0},
        position=(50.0, -1.0),
        review=None,
    )


@pytest.fixture
def arguments(contact: Contact) -> dict:
    return {
        "survey_id": "survey-1",
        "contacts": [contact],
        "claim": ClaimDecision(
            level="calibrated",
            reasons=["Within evaluated conditions."],
            statement="Calibrated estimates for these survey conditions.",
        ),
        "manifest": {
            "model_id": "research-v02",
            "model_class": "research",
            "label": "RESEARCH MODEL — evaluation only",
            "blocking_datasets": [],
            "datasets": [{"id": "survey-training", "licence": "CC0", "tier": "research"}],
            "manifest_sha256": "a" * 64,
        },
        "operating": OperatingSummary(
            method="label-free count threshold",
            threshold=0.5,
            budget_fa_per_unit=0.1,
            unit="image",
            flagged=1,
            recall_estimate=0.75,
            recall_ci=(0.65, 0.85),
            recall_source="held-out surveys, research v0.2",
        ),
        "calibration": {
            "method": "beta",
            "fitted_on": "held-out calibration surveys",
            "test_ece": 0.01,
            "brier_skill": 0.2,
        },
        "created": "2025-01-01T00:00:00Z",
        "inputs": {"sonar.png": "b" * 64},
    }


def test_withdrawn_drops_probabilities_and_recall(arguments: dict) -> None:
    arguments["claim"] = ClaimDecision(
        level="withdrawn", statement="Applicability withdrawn.", reasons=["Outside scope."]
    )
    pack = build_pack(**arguments)
    assert all(row["probability"] is None for row in pack["contacts"])
    assert pack["operating"]["recall_estimate"] is None
    assert pack["operating"]["recall_ci"] is None
    assert any("review only" in sentence for sentence in pack["summary"])
    assert any("claim is withdrawn" in sentence for sentence in pack["summary"])
    assert "0.75" not in render_html(pack)
    assert arguments["contacts"][0].probability == 0.7
    assert arguments["operating"].recall_estimate == 0.75


def test_indicative_keeps_and_marks_probabilities(arguments: dict) -> None:
    arguments["claim"] = ClaimDecision(
        level="indicative", statement="Indicative estimates.", reasons=["Conditions differ."]
    )
    pack = build_pack(**arguments)
    assert pack["contacts"][0]["probability"] == 0.7
    assert pack["contacts"][0]["probability_status"] == "indicative"
    assert pack["operating"]["recall_estimate"] == 0.75
    assert any("conditions differ from the calibration surveys" in s for s in pack["summary"])
    assert "0.7 (indicative)" in render_html(pack)


@pytest.mark.parametrize("model_class", ["research", "product"])
def test_research_banner(arguments: dict, model_class: str) -> None:
    arguments["manifest"]["model_class"] = model_class
    pack = build_pack(**arguments)
    html = render_html(pack)
    if model_class == "research":
        assert pack["banner"] == arguments["manifest"]["label"]
        assert html.index('class="banner"') < html.index("<h1>")
        assert arguments["manifest"]["label"] in html
    else:
        assert "banner" not in pack
        assert '<aside class="banner">' not in html


def test_sorting_is_stable_and_none_last(arguments: dict, contact: Contact) -> None:
    arguments["contacts"] = [
        replace(contact, contact_id="none", probability=None, raw_score=100.0),
        replace(contact, contact_id="low", probability=0.1),
        replace(contact, contact_id="tie-a"),
        replace(contact, contact_id="high-score", raw_score=0.9),
        replace(contact, contact_id="tie-b"),
        replace(contact, contact_id="high-probability", probability=0.9, raw_score=0.1),
    ]
    pack = build_pack(**arguments)
    assert [row["contact_id"] for row in pack["contacts"]] == [
        "high-probability",
        "high-score",
        "tie-a",
        "tie-b",
        "low",
        "none",
    ]


def test_banned_reason(arguments: dict) -> None:
    arguments["claim"] = ClaimDecision(
        level="calibrated",
        statement="Estimates.",
        reasons=["100% detection"],
    )
    with pytest.raises(ValueError, match="100% detection"):
        build_pack(**arguments)


@pytest.mark.parametrize("field", ["image", "calibration", "label", "method"])
def test_other_free_text_is_checked(arguments: dict, contact: Contact, field: str) -> None:
    if field == "image":
        arguments["contacts"] = [replace(contact, image="100% detection")]
    elif field == "calibration":
        arguments["calibration"]["note"] = "100% detection"
    elif field == "label":
        arguments["manifest"]["label"] = "100% detection"
    else:
        arguments["operating"] = replace(arguments["operating"], method="100% detection")
    with pytest.raises(ValueError, match="100% detection"):
        build_pack(**arguments)


def test_hash_verifies_and_tracks_changes(arguments: dict, contact: Contact) -> None:
    pack = build_pack(**arguments)
    unhashed = {key: value for key, value in pack.items() if key != "pack_sha256"}
    canonical = json.dumps(
        unhashed, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    assert sha256(canonical).hexdigest() == pack["pack_sha256"]
    arguments["contacts"] = [replace(contact, raw_score=0.81)]
    assert build_pack(**arguments)["pack_sha256"] != pack["pack_sha256"]


def test_write_and_ledger(arguments: dict, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    pack = build_pack(**arguments)
    ledger = Ledger(tmp_path / "ledger.jsonl")
    calls: list[tuple[str, dict]] = []
    original_append = Ledger.append

    def tracked_append(self: Ledger, kind: str, payload: dict) -> str:
        calls.append((kind, payload))
        return original_append(self, kind, payload)

    monkeypatch.setattr(Ledger, "append", tracked_append)
    without = write_pack(pack, tmp_path / "without")
    with_ledger = write_pack(pack, tmp_path / "with", ledger=ledger)
    assert [path.read_bytes() for path in without] == [path.read_bytes() for path in with_ledger]
    assert calls == [
        (
            "report",
            {
                "survey_id": pack["survey_id"],
                "pack_sha256": pack["pack_sha256"],
                "model_id": pack["model"]["model_id"],
                "claim_level": pack["claim"]["level"],
                "n_contacts": pack["n_contacts"],
            },
        )
    ]
    assert ledger.verify() == []
    assert ledger.head
    assert json.loads(with_ledger[0].read_text(encoding="utf-8")) == pack


def test_html_escapes_image(arguments: dict, contact: Contact) -> None:
    arguments["contacts"] = [replace(contact, image="<script>x</script>.png")]
    html = render_html(build_pack(**arguments))
    assert "&lt;script&gt;x&lt;/script&gt;.png" in html
    assert "<script>" not in html


def test_absent_shadow_is_not_penalised(arguments: dict, contact: Contact) -> None:
    pack = build_pack(**arguments)
    row = pack["contacts"][0]
    assert row["evidence"] == contact.evidence
    assert row["probability"] == contact.probability
    assert row["raw_score"] == contact.raw_score
    assert "no measurable shadow (not penalised)" in render_html(pack)


def test_deterministic(arguments: dict, tmp_path: Path) -> None:
    first = build_pack(**arguments)
    second = build_pack(**arguments)
    assert first == second
    assert render_html(first) == render_html(second)
    paths_a = write_pack(first, tmp_path / "a")
    paths_b = write_pack(second, tmp_path / "b")
    assert [path.read_bytes() for path in paths_a] == [path.read_bytes() for path in paths_b]


def test_no_recall_without_estimate(arguments: dict) -> None:
    arguments["operating"] = replace(arguments["operating"], recall_estimate=None, recall_ci=None)
    pack = build_pack(**arguments)
    assert any("none was supplied" in sentence for sentence in pack["summary"])


def _extras() -> dict:
    return {
        "completeness": {
            "available": True,
            "pd": 0.61,
            "pd_lower90": 0.52,
            "trials": 54,
            "detected": 33,
            "claim_level": "calibrated",
            "method": "transplant",
            "caveat": "Reference objects only.",
            "cells": [{"row": 0}],
        },
        "verification_plan": {
            "entries": [
                {
                    "rank": i,
                    "contact_id": f"c{i}",
                    "p_real": 0.5,
                    "cumulative_expected_real": 0.5 * i,
                }
                for i in range(1, 13)
            ],
            "expected_real_total": 6.0,
            "note": "Sum of probabilities.",
        },
    }


def test_completeness_and_plan_sections(arguments: dict) -> None:
    pack = build_pack(**arguments, **_extras())
    assert pack["completeness"]["pd"] == 0.61 and "cells" not in pack["completeness"]
    assert len(pack["verification_plan"]["entries"]) == 10
    html = render_html(pack)
    assert "Search completeness" in html and "Verification plan" in html and "0.52" in html


def test_withdrawn_withholds_completeness_pd(arguments: dict) -> None:
    arguments["claim"] = ClaimDecision(
        level="withdrawn", statement="Applicability withdrawn.", reasons=["Outside scope."]
    )
    pack = build_pack(**arguments, **_extras())
    assert pack["completeness"]["pd"] is None and pack["completeness"]["pd_lower90"] is None
    assert "0.61" not in render_html(pack)


def test_km2_budget_states_searched_area(arguments: dict) -> None:
    arguments["operating"] = replace(
        arguments["operating"], unit="km2", budget_fa_per_unit=50.0, area_km2=0.04
    )
    text = json.dumps(build_pack(**arguments))
    assert "per km2" in text
    assert "0.04 km2 of insonified seabed" in text


def test_reliability_diagram_is_drawn_not_dumped(arguments: dict) -> None:
    import numpy as np

    from netsight.trust.calibrators import BetaCalibrator
    from netsight.trust.reliability import reliability_comparison

    rng = np.random.default_rng(0)
    s = rng.uniform(0.05, 1, 800)
    y = rng.random(800) < s**2
    arguments["calibration"] = {
        **arguments["calibration"],
        "reliability": reliability_comparison(s, y, s, y, BetaCalibrator().fit(s, y)),
    }
    html = render_html(build_pack(**arguments))
    assert "<svg" in html and "Reliability on held-out surveys" in html
    assert "mean_predicted" not in html  # the bins are drawn, not printed as a table cell


def test_coverage_and_multipass_are_reported(arguments: dict) -> None:
    arguments["coverage"] = {"not_searched_fraction": 0.18, "images": [0.1, 0.26]}
    arguments["completeness"] = {
        "available": True,
        "pd": 0.6,
        "pd_lower90": 0.5,
        "cells": [{"status": "not_searched"}, {"status": "ok"}, {"status": "ok"}],
        "multi_pass": {
            "available": True,
            "passes": 2,
            "overlap_km2": 0.01,
            "overlap_pd_max_median": 0.6,
            "overlap_pd_independent_median": 0.8,
            "note": "between the two values",
        },
    }
    pack = build_pack(**arguments)
    assert pack["coverage"]["not_searched_fraction"] == 0.18
    assert pack["completeness"]["cells_not_searched"] == 1
    html = render_html(pack)
    assert "Coverage" in html and "18%" in html
    assert "Multi-pass" in html and "0.6 to 0.8" in html
