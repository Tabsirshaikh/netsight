"""Build deterministic evidence packs with explicit claim limitations."""

import json
from collections.abc import Mapping, Sequence
from copy import deepcopy
from dataclasses import asdict, dataclass
from hashlib import sha256
from html import escape
from pathlib import Path

from netsight.trust.applicability import ClaimDecision
from netsight.trust.provenance import Ledger
from netsight.trust.wording import check_wording

type EvidenceValue = float | bool | None


@dataclass(frozen=True)
class Contact:
    """One detected contact and its unmodified soft evidence."""

    contact_id: str
    image: str
    box: tuple[float, float, float, float]
    raw_score: float
    probability: float | None
    evidence: dict[str, EvidenceValue]
    position: tuple[float, float] | None
    review: str | None


@dataclass(frozen=True)
class OperatingSummary:
    """Operating point and the source of its recall estimate."""

    method: str
    threshold: float
    budget_fa_per_unit: float
    unit: str
    flagged: int
    recall_estimate: float | None
    recall_ci: tuple[float, float] | None
    recall_source: str


def _validate_wording(value: object) -> None:
    """Check every string, including strings in caller-supplied metadata."""
    if isinstance(value, str):
        violations = check_wording(value)
        if violations:
            raise ValueError(f"Banned wording: {', '.join(map(str, violations))}")
    elif isinstance(value, Mapping):
        for key, item in value.items():
            _validate_wording(key)
            _validate_wording(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            _validate_wording(item)


def _canonical(pack: dict) -> bytes:
    """Serialize the hashable portion of a pack."""
    contents = {key: value for key, value in pack.items() if key != "pack_sha256"}
    return json.dumps(
        contents,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _number(value: float) -> str:
    """Format a number without locale-dependent output."""
    return format(value, ".3g")


def _summary(
    count: int,
    claim: ClaimDecision,
    operating: OperatingSummary,
) -> list[str]:
    """Describe counts and limitations without inventing performance assurances."""
    sentences = [
        f"{count} contacts listed.",
        (
            f"At most {_number(operating.budget_fa_per_unit)} flagged contact(s) per "
            f"{operating.unit} ({operating.flagged} flagged, threshold "
            f"{_number(operating.threshold)}). False alarms are a subset of the flagged "
            "contacts, so they cannot exceed this budget on this survey."
        )
        if "count" in operating.method.lower()
        else (
            f"False-alarm budget: {_number(operating.budget_fa_per_unit)} per "
            f"{operating.unit}, targeted using {operating.method} at threshold "
            f"{_number(operating.threshold)}. No formal budget assurance is supplied "
            "by this report; any such assurance depends on the method's assumptions "
            "and supporting validation."
        ),
    ]
    if claim.level == "withdrawn":
        sentences.extend(
            [
                "Contacts are listed for review only; probabilities are withdrawn.",
                "No recall estimate is given because the claim is withdrawn.",
            ]
        )
    else:
        if claim.level == "indicative":
            sentences.append(
                "Probabilities and recall are indicative: conditions differ from "
                "the calibration surveys."
            )
        if operating.recall_estimate is None:
            sentences.append("No recall estimate is given because none was supplied.")
        else:
            interval = (
                f" with interval [{_number(operating.recall_ci[0])}, "
                f"{_number(operating.recall_ci[1])}]"
                if operating.recall_ci is not None
                else " (no interval supplied)"
            )
            sentences.append(
                f"Recall estimate: {_number(operating.recall_estimate)}{interval}; "
                f"source: {operating.recall_source}."
            )
    return sentences


def build_pack(
    *,
    survey_id: str,
    contacts: Sequence[Contact],
    claim: ClaimDecision,
    manifest: dict,
    operating: OperatingSummary,
    calibration: dict,
    created: str,
    inputs: Mapping[str, str],
) -> dict:
    """Build a detached, JSON-compatible pack and its canonical digest."""
    if claim.level not in {"calibrated", "indicative", "withdrawn"}:
        raise ValueError(f"Unknown claim level: {claim.level}")
    if operating.unit not in {"image", "km2"}:
        raise ValueError(f"Unknown operating unit: {operating.unit}")

    # Validate caller text even when claim restrictions will hide a supplied value.
    _validate_wording(
        {
            "survey_id": survey_id,
            "created": created,
            "contacts": [asdict(contact) for contact in contacts],
            "claim": {
                "level": claim.level,
                "statement": claim.statement,
                "reasons": claim.reasons,
            },
            "manifest": manifest,
            "operating": asdict(operating),
            "calibration": calibration,
            "inputs": inputs,
        }
    )

    contact_rows = []
    for contact in contacts:
        if contact.review not in {None, "confirmed", "rejected"}:
            raise ValueError(f"Unknown review: {contact.review}")
        row = asdict(contact)
        if claim.level == "withdrawn":
            row["probability"] = None
        row["probability_status"] = claim.level
        contact_rows.append(row)

    # Python's stable sort preserves input order for equal probability/score pairs.
    contact_rows.sort(
        key=lambda row: (
            row["probability"] is None,
            -row["probability"] if row["probability"] is not None else 0,
            -row["raw_score"],
        )
    )
    operating_data = asdict(operating)
    if claim.level == "withdrawn":
        operating_data["recall_estimate"] = None
        operating_data["recall_ci"] = None

    pack = {
        "schema_version": "1",
        "survey_id": survey_id,
        "created": created,
        "model": {
            key: manifest[key] for key in ("model_id", "model_class", "label", "manifest_sha256")
        },
        "claim": {
            "level": claim.level,
            "statement": claim.statement,
            "reasons": list(claim.reasons),
        },
        "operating": operating_data,
        "calibration": deepcopy(calibration),
        "inputs": dict(inputs),
        "n_contacts": len(contact_rows),
        "contacts": contact_rows,
        "summary": _summary(len(contact_rows), claim, operating),
    }
    if manifest["model_class"] != "product":
        # A top-level banner makes the research label visible outside model metadata.
        pack = {"banner": manifest["label"], **pack}

    # Normalize tuples to JSON arrays, detach all nested data, and reject NaN/infinity.
    pack = json.loads(_canonical(pack))
    _validate_wording(pack)
    pack["pack_sha256"] = sha256(_canonical(pack)).hexdigest()
    return pack


def _text(value: object) -> str:
    """Convert a value into escaped display text."""
    if value is None:
        text = "not supplied"
    elif isinstance(value, (dict, list, tuple)):
        text = json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False)
    elif isinstance(value, bool):
        text = "true" if value else "false"
    else:
        text = str(value)
    return escape(text, quote=True)


def _table(headers: Sequence[str], rows: Sequence[Sequence[object]]) -> str:
    """Render a horizontally scrollable, escaped table."""
    headings = "".join(f'<th scope="col">{_text(header)}</th>' for header in headers)
    body = "".join(
        "<tr>" + "".join(f"<td>{_text(cell)}</td>" for cell in row) + "</tr>" for row in rows
    )
    return (
        '<div class="table-scroll"><table><thead><tr>'
        f"{headings}</tr></thead><tbody>{body}</tbody></table></div>"
    )


def _evidence_text(evidence: Mapping[str, EvidenceValue]) -> str:
    """Describe soft evidence without treating missing shadows as negative evidence."""
    items = []
    for key, value in sorted(evidence.items()):
        if key == "shadow_present" and value is False:
            items.append("shadow_present=no measurable shadow (not penalised)")
        else:
            if value is None:
                displayed = "not measured"
            elif isinstance(value, bool):
                displayed = "true" if value else "false"
            else:
                displayed = str(value)
            items.append(f"{key}={displayed}")
    return "; ".join(items) or "not supplied"


def render_html(pack: dict) -> str:
    """Render one self-contained report with escaped, non-interactive values."""
    _validate_wording(pack)
    level = pack["claim"]["level"]
    badge_class = {
        "calibrated": "calibrated",
        "indicative": "indicative",
        "withdrawn": "withdrawn",
    }.get(level, "withdrawn")
    banner = ""
    if pack["model"]["model_class"] != "product":
        banner = f'<aside class="banner">{_text(pack["model"]["label"])}</aside>'
    reasons = "".join(f"<li>{_text(reason)}</li>" for reason in pack["claim"]["reasons"])
    summary = "".join(f"<li>{_text(sentence)}</li>" for sentence in pack["summary"])

    rows = []
    for contact in pack["contacts"]:
        probability = contact["probability"]
        if level == "withdrawn":
            probability_text = "withdrawn"
        elif probability is None:
            probability_text = "not supplied"
        elif level == "indicative":
            probability_text = f"{probability} (indicative)"
        else:
            probability_text = str(probability)
        rows.append(
            [
                contact["contact_id"],
                contact["image"],
                contact["box"],
                probability_text,
                contact["raw_score"],
                contact["review"],
                _evidence_text(contact["evidence"]),
            ]
        )

    operating = _table(
        ["Field", "Value"], [[key, value] for key, value in sorted(pack["operating"].items())]
    )
    calibration = _table(
        ["Field", "Value"], [[key, value] for key, value in sorted(pack["calibration"].items())]
    )
    contacts = _table(
        ["ID", "Image", "Box", "Probability", "Raw score", "Review", "Soft evidence"],
        rows,
    )
    inputs = _table(
        ["Input", "SHA-256"], [[key, value] for key, value in sorted(pack["inputs"].items())]
    )
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        "<title>NetSight evidence pack</title><style>"
        "body{font-family:system-ui,sans-serif;margin:0;color:#202020;background:#fafafa}"
        "main{max-width:70rem;margin:auto;padding:1rem}"
        ".banner{background:#ffe4b5;border:2px solid #8a5100;padding:1rem;font-weight:bold}"
        ".badge{display:inline-block;padding:.3rem .7rem;border-radius:.3rem}"
        ".calibrated{background:#d3efda;color:#164326}"
        ".indicative{background:#ffe4a1;color:#513900}"
        ".withdrawn{background:#dedede;color:#333}"
        ".table-scroll{overflow-x:auto;margin-bottom:1rem}"
        "table{border-collapse:collapse;width:100%;background:white}"
        "th,td{border:1px solid #ccc;padding:.5rem;text-align:left;vertical-align:top}"
        "p,li,footer{overflow-wrap:anywhere}footer{margin-top:2rem;font-size:.85rem}"
        "</style></head><body><main>"
        f"{banner}<h1>NetSight evidence pack</h1>"
        f"<p>Survey: {_text(pack['survey_id'])} · Created: {_text(pack['created'])}</p>"
        f"<p>Model: {_text(pack['model']['model_id'])}</p>"
        f'<h2>Claim <span class="badge {badge_class}">{_text(level)}</span></h2>'
        f"<p>{_text(pack['claim']['statement'])}</p><ul>{reasons}</ul>"
        f"<h2>Summary</h2><ul>{summary}</ul>"
        f"<h2>Operating point</h2>{operating}"
        f"<h2>Calibration</h2>{calibration}"
        "<h2>Contacts</h2><p>Soft evidence is descriptive only; it does not "
        "drop or down-weight contacts.</p>"
        f"{contacts}<h2>Inputs</h2>{inputs}"
        f"<footer>Pack SHA-256: {_text(pack['pack_sha256'])}</footer>"
        "</main></body></html>\n"
    )


def write_pack(
    pack: dict,
    out_dir: str | Path,
    *,
    ledger: Ledger | None = None,
) -> tuple[Path, Path]:
    """Write stable report files, then optionally record their pack identity."""
    _validate_wording(pack)
    if pack.get("pack_sha256") != sha256(_canonical(pack)).hexdigest():
        raise ValueError("Pack SHA-256 does not match its contents")
    json_text = (
        json.dumps(pack, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n"
    )
    html_text = render_html(pack)
    directory = Path(out_dir)
    directory.mkdir(parents=True, exist_ok=True)
    json_path = directory / "evidence_pack.json"
    html_path = directory / "evidence_pack.html"
    json_path.write_bytes(json_text.encode("utf-8"))
    html_path.write_bytes(html_text.encode("utf-8"))
    if ledger is not None:
        ledger.append(
            "report",
            {
                "survey_id": pack["survey_id"],
                "pack_sha256": pack["pack_sha256"],
                "model_id": pack["model"]["model_id"],
                "claim_level": pack["claim"]["level"],
                "n_contacts": pack["n_contacts"],
            },
        )
    return json_path, html_path
