import pytest

from netsight.governance.licences import (
    commercial_training_allowed,
    default_allowlist_path,
    default_register_path,
    forbidden_dependencies,
    installed_distributions,
    load_allowlist,
    load_register,
    unknown_licence_dependencies,
    validate_register,
)

GOOD = {
    "id": "a",
    "title": "A",
    "source_url": "https://x",
    "licence": "CC-BY-4.0",
    "licence_status": "verified",
    "commercial_use": "yes",
    "tier": "commercial",
    "files": [],
}


def test_real_register_is_valid():
    entries = load_register(default_register_path())
    assert validate_register(entries) == []
    ids = {e["id"] for e in entries}
    assert {"bodine_substrate", "ai4shipwrecks", "noaa_hsurveys"} <= ids


def test_validation_rules():
    assert validate_register([GOOD]) == []
    assert any("missing" in e for e in validate_register([{"id": "b"}]))
    bad_tier = {**GOOD, "tier": "free"}
    assert any("tier" in e for e in validate_register([bad_tier]))
    unverified_commercial = {**GOOD, "licence_status": "unconfirmed"}
    assert any("commercial" in e for e in validate_register([unverified_commercial]))
    research_yes = {**GOOD, "tier": "research_only", "licence_status": "unconfirmed"}
    assert any("research_only" in e for e in validate_register([research_yes]))
    assert any("duplicate" in e for e in validate_register([GOOD, GOOD]))


def test_commercial_training_gate():
    assert commercial_training_allowed(GOOD)
    assert not commercial_training_allowed({**GOOD, "tier": "conditional"})


def test_commercial_training_gate_fails_closed():
    assert not commercial_training_allowed({**GOOD, "tier": "research_only"})
    assert not commercial_training_allowed({**GOOD, "licence_status": "unconfirmed"})
    assert not commercial_training_allowed({**GOOD, "commercial_use": "conditional"})
    assert not commercial_training_allowed({**GOOD, "commercial_use": True})
    assert not commercial_training_allowed({k: v for k, v in GOOD.items() if k != "files"})
    assert not commercial_training_allowed({**GOOD, "tier": "free"})
    assert not commercial_training_allowed({})
    assert not commercial_training_allowed("a")
    by_id = {e["id"]: e for e in load_register(default_register_path())}
    for dataset_id in ("ghostvision_crabpot", "nksid", "ai4shipwrecks"):
        assert not commercial_training_allowed(by_id[dataset_id])
    assert commercial_training_allowed(by_id["bodine_substrate"])


def test_real_register_consistency():
    by_id = {e["id"]: e for e in load_register(default_register_path())}
    assert by_id["nksid"]["tier"] == "research_only"
    assert by_id["nksid"]["commercial_use"] == "unknown"
    assert by_id["nksid"]["licence_status"] == "unconfirmed"
    assert by_id["jncc_cefas_raw_sss"]["availability"] == "blocked"
    assert by_id["ai4shipwrecks"]["availability"] == "blocked"
    assert by_id["noaa_hsurveys"]["availability"] == "available"


def test_availability_validation():
    for value in ("available", "blocked", "request"):
        assert validate_register([{**GOOD, "availability": value}]) == []
    assert any("availability" in e for e in validate_register([{**GOOD, "availability": "maybe"}]))


def test_commercial_use_must_be_quoted_string():
    errors = validate_register([{**GOOD, "commercial_use": True}])
    assert any("commercial_use must be a quoted string" in e for e in errors)
    errors = validate_register([{**GOOD, "tier": "research_only", "commercial_use": False}])
    assert any("commercial_use must be a quoted string" in e for e in errors)


def test_loader_rejects_malformed_documents(tmp_path):
    def load(text):
        path = tmp_path / "r.yaml"
        path.write_text(text, encoding="utf-8")
        return load_register(path)

    with pytest.raises(ValueError, match="mapping"):
        load("- a\n- b\n")
    with pytest.raises(ValueError, match="datasets"):
        load("other: 1\n")
    with pytest.raises(ValueError, match="datasets"):
        load("")
    with pytest.raises(ValueError, match="list"):
        load("datasets: 3\n")
    with pytest.raises(ValueError, match="entry 1"):
        load("datasets:\n  - {id: a}\n  - just a string\n")
    assert load("datasets:\n  - {id: a}\n") == [{"id": "a"}]


class FakeDist:
    def __init__(self, name, licence="", classifiers=(), expression=""):
        self.metadata = {
            "Name": name,
            "License": licence,
            "License-Expression": expression,
        }
        self._classifiers = list(classifiers)

    def __getattr__(self, item):
        raise AttributeError(item)


def flagged(*dists, allowlist=None):
    return {n for n, _ in forbidden_dependencies(list(dists), allowlist)}


def test_forbidden_dependency_detection():
    gpl_classifier = "License :: OSI Approved :: GNU General Public License v3 (GPLv3)"
    dists = [
        FakeDist("ok", expression="MIT"),
        FakeDist("lgpl", licence="GNU Lesser General Public License v2.1"),
        FakeDist("bad", expression="AGPL-3.0-only"),
        FakeDist("gpl", licence="GPL-3.0-or-later"),
        FakeDist(
            "bundled",
            expression="BSD-3-Clause",
            licence="x" * 300 + " GNU General Public License",
        ),
        FakeDist("classifier", classifiers=[gpl_classifier]),
    ]
    names = {n for n, _ in forbidden_dependencies(dists)}
    assert names == {"bad", "gpl", "classifier"}


GPL_TITLE = "GNU GENERAL PUBLIC LICENSE\n                       Version 3, 29 June 2007\n"


def test_long_licence_field_scans_head_only():
    padding = "\nCopyright (C) 2007 Free Software Foundation, Inc.\n" * 20
    head_gpl = FakeDist("head", licence=GPL_TITLE + padding)
    assert flagged(head_gpl) == {"head"}
    # numpy-style: own licence on top, bundled GPL-with-exception text far below
    deep = "Copyright (c) 2005-2023, NumPy Developers.\n" + padding + GPL_TITLE
    assert len(deep) > 200
    assert flagged(FakeDist("deep", licence=deep)) == set()
    # a long first line is cut at 200 characters
    long_line = "x" * 250 + " GNU General Public License"
    assert flagged(FakeDist("longline", licence=long_line)) == set()
    # leading blank lines are skipped when finding the head
    assert flagged(FakeDist("blank", licence="\n\n" + GPL_TITLE + padding)) == {"blank"}


def test_expression_is_authoritative_over_long_licence_field():
    padding = "\n" + "filler text\n" * 40
    dist = FakeDist("e", expression="MIT", licence=GPL_TITLE + padding)
    assert flagged(dist) == set()


@pytest.mark.parametrize(
    "text",
    [
        "GNU Public License",
        "General Public License v2",
        "GNU General Public License",
        "GNU Affero General Public License v3",
        "Affero",
        "AGPLv3",
        "GPLv2+",
        "GNU GPL",
    ],
)
def test_gpl_spellings_are_flagged(text):
    assert flagged(FakeDist("x", licence=text)) == {"x"}


@pytest.mark.parametrize(
    "text",
    [
        "L-GPL",
        "LGPL",
        "LGPLv3+",
        "GNU Lesser General Public License",
        "GNU Library General Public License",
        "Lesser General Public License v2.1",
        "MIT",
    ],
)
def test_lgpl_spellings_are_allowed(text):
    assert flagged(FakeDist("x", licence=text)) == set()


@pytest.mark.parametrize(
    ("expression", "expected_flagged"),
    [
        ("GPL-2.0-only AND LGPL-2.1-only", True),
        ("GPL-3.0-or-later OR LGPL-3.0", False),
        ("GPL-2.0 OR MIT", False),
        ("GPL-2.0-or-later WITH Classpath-exception-2.0", True),
        ("MIT AND Apache-2.0", False),
        ("GPL-2.0-only OR GPL-3.0-only", True),
        ("(GPL-2.0-only OR MIT) AND Apache-2.0", False),
        ("GPL-2.0-only AND (MIT OR BSD-3-Clause)", True),
        ("MIT AND (Apache-2.0 OR GPL-3.0-only)", False),
        ("AGPL-3.0-or-later", True),
        ("LGPL-2.1-or-later", False),
        ("gpl-2.0 or mit", False),
    ],
)
def test_spdx_expressions_evaluated_per_term(expression, expected_flagged):
    assert (flagged(FakeDist("x", expression=expression)) == {"x"}) is expected_flagged


def test_allowlist_skips_named_dependencies():
    gpl = FakeDist("Some_Pkg", licence="GPL-3.0-or-later")
    other = FakeDist("other", licence="GPL-3.0-or-later")
    assert flagged(gpl, other) == {"Some_Pkg", "other"}
    assert flagged(gpl, other, allowlist=["some-pkg"]) == {"other"}
    assert flagged(gpl, other, allowlist=[]) == {"Some_Pkg", "other"}


def test_allowlist_loader(tmp_path):
    assert load_allowlist(default_allowlist_path()) == []
    path = tmp_path / "a.yaml"
    path.write_text(
        "allowlist:\n  - {name: Foo_Bar, reason: GPL with linking exception, tool only}\n",
        encoding="utf-8",
    )
    assert load_allowlist(path) == ["Foo_Bar"]
    for bad in ("- x\n", "other: 1\n", "allowlist: 3\n", "allowlist:\n  - {name: a}\n"):
        path.write_text(bad, encoding="utf-8")
        with pytest.raises(ValueError):
            load_allowlist(path)


def test_unknown_licence_dependencies_reports_missing_metadata():
    dists = [
        FakeDist("expr", expression="MIT"),
        FakeDist("field", licence="BSD"),
        FakeDist("classifier", classifiers=["License :: OSI Approved :: MIT License"]),
        FakeDist("none"),
        FakeDist("unknown_marker", licence="UNKNOWN"),
        FakeDist("other_classifiers_only", classifiers=["Programming Language :: Python"]),
        FakeDist("Allowed_One"),
    ]
    assert unknown_licence_dependencies(dists, ["allowed-one"]) == [
        "none",
        "unknown_marker",
        "other_classifiers_only",
    ]
    assert "Allowed_One" in unknown_licence_dependencies(dists)


def test_installed_distributions_have_no_forbidden_licences():
    assert forbidden_dependencies(installed_distributions()) == []
