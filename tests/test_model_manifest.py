import json

import pytest

from netsight.models.manifest import (
    ResearchModelError,
    assert_product_release,
    build_training_manifest,
    write_manifest,
)
from netsight.trust.provenance import Ledger

REGISTER = [
    {"id": "clean_cc0", "title": "A", "licence": "CC0-1.0", "tier": "commercial",
     "commercial_use": "yes"},
    {"id": "clean_ccby", "title": "B", "licence": "CC-BY-4.0", "tier": "commercial",
     "commercial_use": "yes"},
    {"id": "clean_mit", "title": "C", "licence": "MIT", "tier": "commercial",
     "commercial_use": "yes"},
    {"id": "share_alike", "title": "D", "licence": "CC-BY-SA-4.0 vs GPL", "tier": "conditional",
     "commercial_use": "conditional"},
    {"id": "no_licence", "title": "E", "licence": "not stated", "tier": "research_only",
     "commercial_use": "unknown"},
]


def _build(ids, **kw):
    return build_training_manifest(
        ids, REGISTER, model_id="det-test", code_version="abc1234", config={"tile": 640}, **kw
    )


def test_all_commercial_is_product_with_notices():
    m = _build(["clean_cc0", "clean_ccby", "clean_mit"])
    assert m["model_class"] == "product" and m["blocking_datasets"] == []
    notices = {n["id"] for n in m["notices_required"]}
    assert notices == {"clean_ccby", "clean_mit"}  # CC0 needs no notice
    assert m["code_version"] == "abc1234" and m["config"] == {"tile": 640}


def test_any_research_only_dataset_makes_a_research_model():
    m = _build(["clean_ccby", "no_licence"])
    assert m["model_class"] == "research"
    assert m["blocking_datasets"] == ["no_licence"]
    assert "not for product" in m["label"]


def test_conditional_licence_also_blocks_product():
    m = _build(["clean_cc0", "share_alike"])
    assert m["model_class"] == "research" and m["blocking_datasets"] == ["share_alike"]


def test_unknown_or_empty_dataset_list_is_rejected():
    with pytest.raises(ValueError):
        _build(["clean_cc0", "not_in_register"])
    with pytest.raises(ValueError):
        _build([])


def test_duplicate_ids_are_listed_once():
    m = _build(["clean_cc0", "clean_cc0"])
    assert [d["id"] for d in m["datasets"]] == ["clean_cc0"]


def test_write_manifest_records_in_ledger(tmp_path):
    m = _build(["clean_ccby", "no_licence"])
    ledger = Ledger(tmp_path / "prov.jsonl")
    path = write_manifest(m, tmp_path / "model", ledger=ledger)
    saved = json.loads(path.read_text(encoding="utf-8"))
    assert saved["model_class"] == "research"
    entry = ledger.entries()[-1]
    assert entry["kind"] == "model" and entry["payload"]["model_id"] == "det-test"
    assert entry["payload"]["manifest_sha256"] == saved["manifest_sha256"]
    assert ledger.verify() == []


def test_product_release_refuses_research_model():
    with pytest.raises(ResearchModelError, match="no_licence"):
        assert_product_release(_build(["no_licence"]))
    assert_product_release(_build(["clean_cc0"]))  # does not raise


def test_fine_tuned_model_inherits_base_datasets(tmp_path):
    from netsight.models.manifest import inherited_dataset_ids

    base = _build(["clean_ccby", "no_licence"])
    write_manifest(base, tmp_path / "base")
    ids = inherited_dataset_ids(["clean_cc0"], tmp_path / "base")
    assert ids == ["clean_cc0", "clean_ccby", "no_licence"]  # own first, then the base's
    m = _build(ids)
    assert m["model_class"] == "research"  # the base used research-only data
    assert inherited_dataset_ids(["clean_cc0"], tmp_path / "no_such_model") == ["clean_cc0"]
