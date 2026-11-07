"""Wording rules for every report and label (plan section 13.3, labelling guide section 7).

`check_wording` returns the banned claims found in a text; generated reports must return [].
Negated uses ("does not certify", "not cleared") are allowed.
"""

from __future__ import annotations

import re

DISCLAIMER = (
    "NetSight provides a probabilistic second-opinion assessment of the supplied data. "
    "It does not certify the absence of objects. No single survey system can guarantee "
    "detection of all features. Residual risk remains and must be managed by the duty holder "
    "under the project's ALARP process. Not for navigation."
)

_BANNED: dict[str, str] = {
    "area declared clear or safe": (
        r"\b(?:channel|area|site|seabed|block|route)\b[^.]{0,40}?\b(?:is|are)\s+(?:now\s+)?"
        r"(?:clear|safe)\b"
    ),
    "safe to dredge/anchor/dive/navigate": r"\bsafe to (?:dredge|anchor|dive|navigate)\b",
    "clear of objects": r"\bclear of (?:nets?|debris|objects?|uxo|obstructions?|hazards?)\b",
    "cleared": r"(?<!not )\bcleared\b",
    "no objects present": (
        r"\bno (?:objects?|targets?|debris|nets?|contacts?|uxo) (?:are )?(?:present|exist|remain)"
    ),
    "confirmed identity without diver/ROV": r"\bconfirmed (?:ghost )?(?:nets?|gear|uxo)\b",
    "AI-verified": r"\bai[- ]verified\b",
    "works on any sonar": r"\bworks (?:on|with) (?:any|all|every) sonars?\b",
    "certified (before accreditation)": r"(?<!not )(?<!never )\bcertif(?:ied|ies|y|ication)\b",
    "100% detection": r"\b100\s*%\s*(?:detection|detected|coverage guaranteed)",
    "guaranteed": r"\bguaranteed\b|\b(?:we|fully|is|are)\s+guarantee[sd]?\b",
}
_COMPILED = {name: re.compile(p, re.IGNORECASE) for name, p in _BANNED.items()}


def banned_phrases() -> list[str]:
    return list(_BANNED)


def check_wording(text: str) -> list[str]:
    """Banned claims found in `text`, as 'rule: matched text'; empty when the text is safe."""
    found = []
    for name, rx in _COMPILED.items():
        for m in rx.finditer(text):
            found.append(f"{name}: {m.group(0)!r}")
    return found
