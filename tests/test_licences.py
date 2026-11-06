from netsight.governance.licences import (
    commercial_training_allowed,
    default_register_path,
    forbidden_dependencies,
    installed_distributions,
    load_register,
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


def test_installed_distributions_have_no_forbidden_licences():
    assert forbidden_dependencies(installed_distributions()) == []
