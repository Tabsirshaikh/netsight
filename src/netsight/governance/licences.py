"""Licence register validation and dependency licence scan (WP0)."""

from __future__ import annotations

import re
from importlib import metadata as importlib_metadata
from pathlib import Path

import yaml

from netsight.config import repo_root

REQUIRED_KEYS = (
    "id",
    "title",
    "source_url",
    "licence",
    "licence_status",
    "commercial_use",
    "tier",
    "files",
)
TIERS = {"commercial", "conditional", "research_only"}
STATUSES = {"verified", "conflict", "unconfirmed"}
_GPL = re.compile(r"\bA?GPL|GNU (Affero )?General Public", re.IGNORECASE)
_LGPL = re.compile(r"\bLGPL|Lesser General Public", re.IGNORECASE)


def default_register_path() -> Path:
    return repo_root() / "licences" / "datasets.yaml"


def load_register(path: str | Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        doc = yaml.safe_load(f) or {}
    return list(doc.get("datasets", []))


def validate_register(entries: list[dict]) -> list[str]:
    errors: list[str] = []
    seen: set[str] = set()
    for i, e in enumerate(entries):
        label = e.get("id", f"entry {i}")
        missing = [k for k in REQUIRED_KEYS if k not in e]
        if missing:
            errors.append(f"{label}: missing keys {missing}")
            continue
        if e["id"] in seen:
            errors.append(f"{label}: duplicate id")
        seen.add(e["id"])
        if e["tier"] not in TIERS:
            errors.append(f"{label}: tier must be one of {sorted(TIERS)}")
        if e["licence_status"] not in STATUSES:
            errors.append(f"{label}: licence_status must be one of {sorted(STATUSES)}")
        commercial_use = str(e["commercial_use"]).lower()
        if e["tier"] == "commercial" and (
            e["licence_status"] != "verified" or commercial_use != "yes"
        ):
            errors.append(
                f"{label}: tier commercial needs licence_status verified and commercial_use yes"
            )
        if e["tier"] == "research_only" and commercial_use not in ("no", "unknown"):
            errors.append(f"{label}: tier research_only needs commercial_use no or unknown")
    return errors


def commercial_training_allowed(entry: dict) -> bool:
    return entry.get("tier") == "commercial"


MAX_SHORT_LICENCE_FIELD = 200


def licence_strings(dist) -> list[str]:
    """SPDX expression if present (authoritative); else a short License field; plus classifiers.

    Long License fields are full licence texts that often quote bundled third-party licences
    (numpy wheels mention the GPL'd gfortran runtime, which carries a linking exception), so they
    are not scanned.
    """
    md = dist.metadata
    expression = md.get("License-Expression") or ""
    licence = md.get("License") or ""
    short_licence = [licence] if len(licence) <= MAX_SHORT_LICENCE_FIELD else []
    out = [expression] if expression else short_licence
    classifiers = getattr(dist, "_classifiers", None)
    if classifiers is None:
        classifiers = (md.get_all("Classifier") or []) if hasattr(md, "get_all") else []
    out += [c for c in classifiers if c.startswith("License ::")]
    return [s for s in out if s]


def forbidden_dependencies(dists) -> list[tuple[str, str]]:
    bad = []
    for d in dists:
        for text in licence_strings(d):
            if _GPL.search(text) and not _LGPL.search(text):
                bad.append((d.metadata.get("Name", "?"), text))
                break
    return bad


def installed_distributions() -> list:
    return list(importlib_metadata.distributions())
