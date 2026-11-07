import json
import math

import pytest

from netsight.trust.provenance import GENESIS, Ledger
from netsight.trust.wording import DISCLAIMER, banned_phrases, check_wording


def _clock():
    t = iter(range(1000))
    return lambda: f"2026-11-07T00:00:{next(t):02d}Z"


# --- hash-chained ledger ---------------------------------------------------------------------


def test_append_chains_hashes_and_verifies(tmp_path):
    led = Ledger(tmp_path / "prov.jsonl", clock=_clock())
    h1 = led.append("data", {"file": "a.xtf", "sha256": "ab" * 32})
    h2 = led.append("model", {"model_id": "det-0.1"})
    entries = led.entries()
    assert [e["seq"] for e in entries] == [0, 1]
    assert entries[0]["prev_hash"] == GENESIS and entries[1]["prev_hash"] == h1
    assert entries[1]["hash"] == h2 and led.head == h2
    assert led.verify() == []


def test_reopen_continues_the_chain(tmp_path):
    path = tmp_path / "prov.jsonl"
    first = Ledger(path, clock=_clock())
    h1 = first.append("data", {"x": 1})
    second = Ledger(path, clock=_clock())
    assert second.head == h1
    second.append("run", {"y": 2})
    assert second.verify() == [] and len(second.entries()) == 2


def test_edit_is_detected(tmp_path):
    path = tmp_path / "prov.jsonl"
    led = Ledger(path, clock=_clock())
    led.append("contact", {"contact_id": "C1", "p_real": 0.2})
    led.append("contact", {"contact_id": "C2", "p_real": 0.9})
    lines = path.read_text(encoding="utf-8").splitlines()
    tampered = json.loads(lines[0])
    tampered["payload"]["p_real"] = 0.99
    lines[0] = json.dumps(tampered)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    problems = Ledger(path, clock=_clock()).verify()
    assert any("seq 0" in p and "hash" in p for p in problems)


def test_deleted_entry_is_detected(tmp_path):
    path = tmp_path / "prov.jsonl"
    led = Ledger(path, clock=_clock())
    for i in range(3):
        led.append("run", {"i": i})
    lines = path.read_text(encoding="utf-8").splitlines()
    path.write_text("\n".join([lines[0], lines[2]]) + "\n", encoding="utf-8")
    problems = Ledger(path, clock=_clock()).verify()
    assert problems and any("seq" in p for p in problems)


def test_review_and_verification_are_distinct_kinds(tmp_path):
    led = Ledger(tmp_path / "p.jsonl", clock=_clock())
    led.append("review", {"contact_id": "C1", "disposition": "verified_real", "by": "expert"})
    led.append("verification", {"contact_id": "C1", "method": "diver", "outcome": "real"})
    assert [e["kind"] for e in led.entries()] == ["review", "verification"]


@pytest.mark.parametrize(
    ("kind", "payload"),
    [
        ("opinion", {"x": 1}),  # unknown kind
        ("run", {"x": math.nan}),  # NaN is not valid JSON
        ("run", {"x": object()}),  # not serialisable
        ("run", ["not", "a", "dict"]),
    ],
)
def test_bad_entries_rejected_and_nothing_written(tmp_path, kind, payload):
    path = tmp_path / "p.jsonl"
    led = Ledger(path, clock=_clock())
    with pytest.raises(ValueError):
        led.append(kind, payload)
    assert not path.exists() or path.read_text(encoding="utf-8") == ""


def test_hash_does_not_depend_on_key_order(tmp_path):
    a = Ledger(tmp_path / "a.jsonl", clock=_clock()).append("run", {"x": 1, "y": 2})
    b = Ledger(tmp_path / "b.jsonl", clock=_clock()).append("run", {"y": 2, "x": 1})
    assert a == b


# --- wording guard ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "The channel is clear of debris.",
        "This area is safe to anchor.",
        "Confirmed ghost net at 12 m.",
        "AI-verified contacts",
        "NetSight works on any sonar",
        "Certified clearance report",
        "100% detection",
        "Detection is guaranteed",
        "No objects present in block 4",
        "Area cleared of nets",
    ],
)
def test_banned_wording_is_flagged(text):
    assert check_wording(text)


@pytest.mark.parametrize(
    "text",
    [
        "Candidate contact, potential ghost-gear contact; not verified by diver or ROV.",
        "Cells shown green had an estimated Pd of at least 0.8 (90% lower bound) for a 1 m cube.",
        DISCLAIMER,
    ],
)
def test_safe_wording_passes(text):
    assert check_wording(text) == []


def test_disclaimer_contains_required_statements():
    for part in ("does not certify the absence of objects", "Not for navigation", "ALARP"):
        assert part in DISCLAIMER


def test_banned_phrases_listed():
    assert len(banned_phrases()) >= 10
