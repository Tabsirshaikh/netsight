"""One-page PDF evidence pack with the disclaimer (plan section 16 item 10).

Rendered from the finished pack dictionary only, so it can never say more than the pack: claim
level and reasons, operating point, calibration, coverage, completeness, top 10 contacts, the
research banner when the model is not a product model, and the disclaimer.
"""

from __future__ import annotations

import io
from typing import Any

from netsight.trust.wording import DISCLAIMER

PAGE_W, PAGE_H = 595.28, 841.89  # A4 in points
MARGIN = 40
BADGE = {
    "calibrated": (0.83, 0.94, 0.85),
    "indicative": (1.0, 0.89, 0.63),
    "withdrawn": (0.87, 0.87, 0.87),
}
SERIES = {
    "NetSight (beta)": (0.17, 0.71, 0.60),
    "B1 temperature": (0.85, 0.64, 0.25),
    "B0 raw score": (0.54, 0.59, 0.65),
}


def _latin(value: object) -> str:
    """Built-in PDF fonts cover cp1252 only; never fail on other characters."""
    text = "-" if value is None else str(value)
    return text.encode("cp1252", "replace").decode("cp1252")


def _num(value: object, digits: int = 3) -> str:
    if value is None:
        return "-"
    if isinstance(value, float):
        return format(value, f".{digits}g")
    return _latin(value)


def _pct(value: object) -> str:
    return "-" if value is None else f"{100 * float(value):.0f}%"


def render_pdf(pack: dict[str, Any]) -> bytes:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.utils import simpleSplit
    from reportlab.pdfgen import canvas

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4, pageCompression=1, invariant=1)  # reproducible bytes
    c.setTitle("NetSight evidence pack")
    c.setAuthor("NetSight")
    width = PAGE_W - 2 * MARGIN
    y = PAGE_H - MARGIN

    def text(s: str, x: float, yy: float, size: float = 9, bold: bool = False) -> None:
        c.setFont("Helvetica-Bold" if bold else "Helvetica", size)
        c.drawString(x, yy, _latin(s))

    def para(s: str, yy: float, size: float = 8.5, w: float = width, x: float = MARGIN) -> float:
        c.setFont("Helvetica", size)
        for line in simpleSplit(_latin(s), "Helvetica", size, w):
            c.drawString(x, yy, line)
            yy -= size + 2.5
        return yy

    text("NetSight evidence pack", MARGIN, y - 4, 16, bold=True)
    y -= 20
    text(
        f"Survey {pack['survey_id']}  |  created {pack['created']}  |  "
        f"model {pack['model']['model_id']}",
        MARGIN,
        y,
        8,
    )
    y -= 14
    if pack.get("banner"):
        lines = simpleSplit(_latin(pack["banner"]), "Helvetica-Bold", 9, width - 16)
        h = 8 + 12 * len(lines)
        c.setFillColorRGB(1.0, 0.89, 0.71)
        c.setStrokeColorRGB(0.54, 0.32, 0.0)
        c.rect(MARGIN, y - h + 6, width, h, fill=1, stroke=1)
        c.setFillColorRGB(0, 0, 0)
        for i, line in enumerate(lines):
            text(line, MARGIN + 8, y - 6 - 12 * i, 9, bold=True)
        y -= h + 8

    level = pack["claim"]["level"]
    badge_bottom = y - 14
    c.setFillColorRGB(*BADGE.get(level, (0.9, 0.9, 0.9)))
    c.roundRect(MARGIN, y - 14, 90, 16, 3, fill=1, stroke=0)
    c.setFillColorRGB(0, 0, 0)
    text(f"Claim: {level}", MARGIN + 6, y - 9, 9, bold=True)
    y = para(pack["claim"]["statement"], y - 2, 9, width - 100, MARGIN + 100) - 2
    y = min(y, badge_bottom - 12)
    for reason in pack["claim"]["reasons"][:3]:
        y = para(f"- {reason}", y, 8)
    y -= 6

    # Key figures (left) and reliability chart (right)
    op = pack["operating"]
    rows: list[tuple[str, str]] = [
        ("Contacts listed", str(pack["n_contacts"])),
        ("Flagged", f"{op['flagged']} (threshold {_num(op['threshold'], 4)})"),
        ("False-alarm budget", f"{_num(op['budget_fa_per_unit'])} per {op['unit']}"),
    ]
    if op.get("area_km2"):
        rows.append(("Searched seabed", f"{_num(op['area_km2'])} km2"))
    ci = op.get("recall_ci")
    rows.append(
        (
            "Validation recall",
            f"{_pct(op.get('recall_estimate'))}"
            + (f" ({_pct(ci[0])}-{_pct(ci[1])})" if ci else ""),
        )
    )
    cal = pack.get("calibration", {})
    rel = cal.get("reliability")
    if rel:
        m = rel["methods"]
        rows.append(
            (
                "Held-out calibration error",
                f"NetSight {m['NetSight (beta)']['ece']:.3f} vs raw score "
                f"{m['B0 raw score']['ece']:.3f}",
            )
        )
    cov = pack.get("coverage")
    if cov:
        rows.append(("Not searched", f"{_pct(cov['not_searched_fraction'])} of the imaged area"))
    comp = pack.get("completeness")
    if comp and comp.get("available", True) and comp.get("pd") is not None:
        rows.append(
            ("Search completeness", f"Pd {_pct(comp['pd'])}, 90% lower {_pct(comp['pd_lower90'])}")
        )
        mp = comp.get("multi_pass") or {}
        if mp.get("overlap_pd_max_median") is not None:
            rows.append(
                (
                    "Multi-pass overlap",
                    f"Pd {_pct(mp['overlap_pd_max_median'])} to "
                    f"{_pct(mp['overlap_pd_independent_median'])}",
                )
            )
    plan = pack.get("verification_plan")
    if plan and plan.get("expected_real_total") is not None:
        rows.append(("Expected real finds", _num(plan["expected_real_total"])))
    table_w = width * 0.58
    top = y
    for label, value in rows:
        text(label, MARGIN, y, 8.5, bold=True)
        text(value, MARGIN + 130, y, 8.5)
        y -= 13
    if rel:
        _reliability(c, rel, MARGIN + table_w + 20, top - 150, 140)
        y = min(y, top - 215)  # chart + legend sit beside the figures
    y -= 6

    contacts = pack["contacts"]
    text(f"Contacts by P(real) (top 10 of {len(contacts)})", MARGIN, y, 10, bold=True)
    y -= 14
    cols = [MARGIN, MARGIN + 40, MARGIN + 110, MARGIN + 330, MARGIN + 400]
    for x, h in zip(cols, ("Rank", "Contact", "Image", "P(real)", "Raw score"), strict=True):
        text(h, x, y, 8, bold=True)
    y -= 11
    for rank, row in enumerate(contacts[:10], 1):
        image = _latin(row["image"])
        image = image if len(image) <= 40 else image[:37] + "..."
        values = (
            str(rank),
            row["contact_id"],
            image,
            _pct(row["probability"]),
            f"{row['raw_score']:.3f}",
        )
        for x, v in zip(cols, values, strict=True):
            text(v, x, y, 8)
        y -= 11

    # Footer: disclaimer and identity
    c.setStrokeColorRGB(0.6, 0.6, 0.6)
    footer_top = MARGIN + 70
    c.line(MARGIN, footer_top, PAGE_W - MARGIN, footer_top)
    yy = para("Disclaimer: " + DISCLAIMER, footer_top - 12, 8)
    para(
        f"Pack SHA-256: {pack['pack_sha256']}. Full pack: evidence_pack.json / .html.",
        yy - 2,
        7,
    )
    c.showPage()
    c.save()
    return buffer.getvalue()


def _reliability(c: Any, rel: dict, x: float, y: float, size: float) -> None:
    """Small reliability diagram: shown P(real) vs observed real rate, held-out surveys."""
    c.setStrokeColorRGB(0.6, 0.6, 0.6)
    c.rect(x, y, size, size, fill=0, stroke=1)
    c.setDash(3, 2)
    c.line(x, y, x + size, y + size)
    c.setDash()
    c.setFont("Helvetica", 7)
    c.drawString(x, y - 9, "0")
    c.drawRightString(x + size, y - 9, "1  shown P(real)")
    c.drawString(x - 8, y + size - 6, "1")
    c.drawString(x, y + size + 4, "Reliability, held-out surveys")
    for i, (name, method) in enumerate(rel["methods"].items()):
        c.setStrokeColorRGB(*SERIES.get(name, (0, 0, 0)))
        c.setLineWidth(1.5)
        pts = [
            (x + b["mean_predicted"] * size, y + b["observed_rate"] * size) for b in method["bins"]
        ]
        for a, b in zip(pts, pts[1:], strict=False):
            c.line(a[0], a[1], b[0], b[1])
        c.setFillColorRGB(*SERIES.get(name, (0, 0, 0)))
        c.rect(x, y - 22 - 10 * i, 8, 3, fill=1, stroke=0)
        c.setFillColorRGB(0, 0, 0)
        c.drawString(x + 12, y - 23 - 10 * i, _latin(f"{name}: ECE {method['ece']:.3f}"))
    c.setLineWidth(1)
