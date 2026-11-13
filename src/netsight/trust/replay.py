"""Provenance replay and tamper checks for evidence packs (plan WP9).

``verify_pack`` checks that a saved pack is exactly what NetSight wrote: the JSON's hash
matches its contents, the hash-chained ledger is intact and records this pack and its PDF,
and the HTML and PDF re-render byte for byte from the JSON. Re-running the detector on the
saved inputs (``replay``) lives in the dashboard server, which holds the model.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


def verify_pack(pack_dir: str | Path, ledger_path: str | Path) -> list[str]:
    """Problems found; an empty list means the pack and its ledger record are intact."""
    from netsight.report.evidence_pack import _canonical, render_html
    from netsight.report.pdf import render_pdf
    from netsight.trust.provenance import Ledger

    pack_dir = Path(pack_dir)
    problems: list[str] = []
    try:
        pack = json.loads((pack_dir / "evidence_pack.json").read_text("utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"evidence_pack.json unreadable: {exc}"]
    stated = pack.pop("pack_sha256", None)
    actual = hashlib.sha256(_canonical(pack)).hexdigest()
    pack["pack_sha256"] = stated
    if stated != actual:
        problems.append("evidence_pack.json does not match its contents (edited after writing)")

    ledger = Ledger(ledger_path)
    problems += [f"ledger: {p}" for p in ledger.verify()]
    try:
        entries = ledger.entries() if Path(ledger_path).exists() else []
    except (json.JSONDecodeError, KeyError) as exc:
        problems.append(f"ledger unreadable: {exc}")
        entries = []
    records = [
        e["payload"]
        for e in entries
        if e.get("kind") == "report" and e.get("payload", {}).get("pack_sha256") == stated
    ]
    if not records:
        problems.append("this pack is not in the ledger")

    if stated == actual:  # re-rendering a forged pack would only repeat the forgery
        html = pack_dir / "evidence_pack.html"
        if not html.exists() or html.read_text("utf-8") != render_html(pack):
            problems.append("HTML report differs from the pack it was written from")
        pdf_path = pack_dir / "evidence_pack.pdf"
        if pdf_path.exists():
            pdf = pdf_path.read_bytes()
            if pdf != render_pdf(pack):
                problems.append("PDF differs from the pack it was written from")
            ledger_pdf = records[-1].get("pdf_sha256") if records else None
            if ledger_pdf and ledger_pdf != hashlib.sha256(pdf).hexdigest():
                problems.append("PDF hash does not match the ledger")
    return problems


def main(argv: list[str] | None = None) -> int:
    import argparse

    p = argparse.ArgumentParser(description="Check an evidence pack against its ledger.")
    p.add_argument("pack_dir")
    p.add_argument("ledger")
    a = p.parse_args(argv)
    problems = verify_pack(a.pack_dir, a.ledger)
    print("\n".join(problems) if problems else "pack and ledger record intact")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
