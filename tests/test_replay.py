import json

import pytest

from netsight.report import Contact, OperatingSummary, build_pack, write_pack
from netsight.trust.applicability import ClaimDecision
from netsight.trust.provenance import Ledger
from netsight.trust.replay import verify_pack


@pytest.fixture
def written(tmp_path):
    pack = build_pack(
        survey_id="s1",
        contacts=[Contact("c1", "a.png", (1, 2, 3, 4), 0.6, 0.9, {}, None, None)],
        claim=ClaimDecision(level="calibrated", reasons=[], statement="Calibrated."),
        manifest={
            "model_id": "m",
            "model_class": "research",
            "label": "RESEARCH",
            "manifest_sha256": "a" * 64,
        },
        operating=OperatingSummary(
            "label-free count threshold", 0.5, 1.0, "image", 1, 0.4, (0.3, 0.5), "val"
        ),
        calibration={"method": "beta"},
        created="2026-11-13T00:00:00Z",
        inputs={"a.png": "b" * 64},
    )
    ledger = Ledger(tmp_path / "ledger.jsonl")
    write_pack(pack, tmp_path / "pack", ledger=ledger)
    return tmp_path / "pack", tmp_path / "ledger.jsonl"


def test_untouched_pack_verifies(written):
    assert verify_pack(*written) == []


def test_edited_pack_json_is_caught(written):
    pack_dir, ledger = written
    path = pack_dir / "evidence_pack.json"
    pack = json.loads(path.read_text("utf-8"))
    pack["contacts"][0]["probability"] = 0.99
    path.write_text(json.dumps(pack), "utf-8")
    problems = verify_pack(pack_dir, ledger)
    assert any("does not match its contents" in p for p in problems)


def test_edited_pdf_and_html_are_caught(written):
    pack_dir, ledger = written
    (pack_dir / "evidence_pack.pdf").write_bytes(b"%PDF-1.4 forged")
    (pack_dir / "evidence_pack.html").write_text("<p>forged</p>", "utf-8")
    problems = " ".join(verify_pack(pack_dir, ledger))
    assert "PDF" in problems and "HTML" in problems


def test_edited_ledger_is_caught(written):
    pack_dir, ledger = written
    entry = json.loads(ledger.read_text("utf-8").splitlines()[0])
    entry["payload"]["claim_level"] = "withdrawn"
    ledger.write_text(json.dumps(entry) + "\n", "utf-8")
    assert any("hash mismatch" in p for p in verify_pack(pack_dir, ledger))


def test_pack_missing_from_ledger_is_caught(written, tmp_path):
    pack_dir, _ = written
    assert any("not in the ledger" in p for p in verify_pack(pack_dir, tmp_path / "empty.jsonl"))
