"""Licence register validation and dependency licence scan (WP0)."""

from __future__ import annotations

import re
from collections.abc import Iterable
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
AVAILABILITIES = {"available", "blocked", "request"}

# LGPL spellings are removed before looking for GPL, so "GPL-3.0 OR LGPL-3.0" text still
# reports the GPL part while "GNU Lesser General Public License" does not.
_LGPL = re.compile(
    r"\bL-?GPL\w*|\b(?:GNU\s+)?(?:Lesser|Library)\s+General\s+Public(?:\s+Licen[sc]e)?",
    re.IGNORECASE,
)
_GPL = re.compile(
    r"\bA?GPL|\bGNU\s+(?:Affero\s+)?(?:General\s+)?Public|\bGeneral\s+Public\s+Licen|\bAffero",
    re.IGNORECASE,
)
MAX_SHORT_LICENCE_FIELD = 200


def default_register_path() -> Path:
    return repo_root() / "licences" / "datasets.yaml"


def default_allowlist_path() -> Path:
    return repo_root() / "licences" / "dependency_allowlist.yaml"


def load_register(path: str | Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        doc = yaml.safe_load(f)
    if not isinstance(doc, dict):
        raise ValueError(f"{path}: the register must be a YAML mapping with a 'datasets' key")
    if "datasets" not in doc:
        raise ValueError(f"{path}: missing 'datasets' key")
    entries = doc["datasets"]
    if not isinstance(entries, list):
        raise ValueError(f"{path}: 'datasets' must be a list")
    for i, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ValueError(f"{path}: entry {i} must be a mapping, got {type(entry).__name__}")
    return entries


def validate_register(entries: list[dict]) -> list[str]:
    errors: list[str] = []
    seen: set[str] = set()
    for i, e in enumerate(entries):
        if not isinstance(e, dict):
            errors.append(f"entry {i}: must be a mapping")
            continue
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
        if "availability" in e and e["availability"] not in AVAILABILITIES:
            errors.append(f"{label}: availability must be one of {sorted(AVAILABILITIES)}")
        if not isinstance(e["commercial_use"], str):
            errors.append(
                f"{label}: commercial_use must be a quoted string "
                '(write "yes" or "no": unquoted yes/no become booleans in YAML)'
            )
            continue
        commercial_use = e["commercial_use"].lower()
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
    """Fail closed: only a valid, verified, commercial-tier entry with commercial_use "yes"."""
    if not isinstance(entry, dict) or validate_register([entry]):
        return False
    return (
        entry["tier"] == "commercial"
        and entry["licence_status"] == "verified"
        and entry["commercial_use"] == "yes"
    )


def _normalise_name(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def load_allowlist(path: str | Path) -> list[str]:
    """Names of dependencies exempt from the licence scan; every entry needs a reason."""
    with open(path, encoding="utf-8") as f:
        doc = yaml.safe_load(f)
    if not isinstance(doc, dict) or "allowlist" not in doc:
        raise ValueError(f"{path}: expected a YAML mapping with an 'allowlist' key")
    entries = doc["allowlist"]
    if not isinstance(entries, list):
        raise ValueError(f"{path}: 'allowlist' must be a list")
    names = []
    for i, entry in enumerate(entries):
        if not isinstance(entry, dict) or not entry.get("name") or not entry.get("reason"):
            raise ValueError(f"{path}: allowlist entry {i} needs a name and a reason")
        names.append(str(entry["name"]))
    return names


def _licence_parts(dist) -> tuple[str, str, list[str]]:
    """Return (SPDX expression, License field, License classifiers), blanks removed."""
    md = dist.metadata
    expression = (md.get("License-Expression") or "").strip()
    licence = (md.get("License") or "").strip()
    if licence.upper() == "UNKNOWN":
        licence = ""
    classifiers = getattr(dist, "_classifiers", None)
    if classifiers is None:
        classifiers = (md.get_all("Classifier") or []) if hasattr(md, "get_all") else []
    return expression, licence, [c for c in classifiers if c.startswith("License ::")]


def _licence_head(licence: str) -> str:
    """The text to scan for a License field.

    Short fields are scanned whole. A long field is a full licence text: it names itself on the
    first line ("GNU GENERAL PUBLIC LICENSE Version 3"), while mentions of bundled third-party
    licences (numpy wheels quote the GPL'd gfortran runtime, with its linking exception) come much
    later, so only the first non-empty line, cut at 200 characters, is scanned.
    """
    if len(licence) <= MAX_SHORT_LICENCE_FIELD:
        return licence
    first_line = next((ln.strip() for ln in licence.splitlines() if ln.strip()), "")
    return first_line[:MAX_SHORT_LICENCE_FIELD]


def licence_strings(dist) -> list[str]:
    """SPDX expression if present (authoritative over the License field), plus classifiers."""
    expression, licence, classifiers = _licence_parts(dist)
    return [s for s in [expression or _licence_head(licence), *classifiers] if s]


def _is_gpl_text(text: str) -> bool:
    return bool(_GPL.search(_LGPL.sub(" ", text)))


def _expression_is_forbidden(expression: str) -> bool:
    """Evaluate an SPDX expression: AND needs every term allowed, OR needs one allowed.

    AND binds tighter than OR; parentheses group; "WITH <exception>" is dropped from a term.
    A GPL/AGPL (non-LGPL) term is forbidden, so an OR may be satisfied by choosing a permissive
    alternative. Malformed input is parsed leniently, never raising.
    """
    tokens = re.findall(r"[()]|[^\s()]+", expression)
    pos = 0

    def peek() -> str:
        return tokens[pos].upper() if pos < len(tokens) else ""

    def parse_or() -> bool:
        nonlocal pos
        forbidden = [parse_and()]
        while peek() == "OR":
            pos += 1
            forbidden.append(parse_and())
        return all(forbidden)

    def parse_and() -> bool:
        nonlocal pos
        forbidden = [parse_term()]
        while peek() == "AND":
            pos += 1
            forbidden.append(parse_term())
        return any(forbidden)

    def parse_term() -> bool:
        nonlocal pos
        if peek() == "(":
            pos += 1
            forbidden = parse_or()
            if peek() == ")":
                pos += 1
            return forbidden
        if pos >= len(tokens):
            return False
        token = tokens[pos]
        pos += 1
        if peek() == "WITH":
            pos += 2
        return _is_gpl_text(token)

    result = parse_or()
    # Tokens left over (stray ")" or missing operators) are checked too, so odd input fails closed.
    return result or any(_is_gpl_text(t) for t in tokens[pos:])


def forbidden_dependencies(dists, allowlist: Iterable[str] | None = None) -> list[tuple[str, str]]:
    allowed = {_normalise_name(n) for n in allowlist or ()}
    bad = []
    for d in dists:
        name = d.metadata.get("Name", "?")
        if _normalise_name(name) in allowed:
            continue
        expression, licence, classifiers = _licence_parts(d)
        if expression:
            candidates = [(expression, _expression_is_forbidden(expression))]
        else:
            head = _licence_head(licence)
            candidates = [(head, _is_gpl_text(head))] if head else []
        candidates += [(c, _is_gpl_text(c)) for c in classifiers]
        hit = next((text for text, is_bad in candidates if is_bad), None)
        if hit is not None:
            bad.append((name, hit))
    return bad


def unknown_licence_dependencies(dists, allowlist: Iterable[str] | None = None) -> list[str]:
    """Names with no SPDX expression, License field or License classifier (a report only)."""
    allowed = {_normalise_name(n) for n in allowlist or ()}
    unknown = []
    for d in dists:
        name = d.metadata.get("Name", "?")
        if _normalise_name(name) in allowed:
            continue
        if not any(_licence_parts(d)):
            unknown.append(name)
    return unknown


def installed_distributions() -> list:
    return list(importlib_metadata.distributions())
