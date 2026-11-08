"""Build an offline NOAA chip reviewer and apply its downloaded decisions."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import math
import shutil
from pathlib import Path
from typing import Any

from PIL import Image

from netsight.datasets.noaa_chips import _safe_component

_DECISIONS = ("keep", "move", "reject", "unsure")


def _load_records(root: Path) -> list[tuple[dict[str, Any], Path]]:
    """Load survey manifests in a reproducible order."""
    records: list[tuple[dict[str, Any], Path]] = []
    seen: set[tuple[str, str]] = set()
    for manifest in sorted(root.glob("*/manifest.json")):
        data = json.loads(manifest.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            raise ValueError(f"Expected a list in {manifest}")
        for record in data:
            identity = (record["survey_id"], record["contact_id"])
            if identity in seen:
                raise ValueError(f"Duplicate survey/contact id: {identity!r}")
            seen.add(identity)
            name = f"{record['survey_id']}_{_safe_component(record['contact_id'])}.png"
            records.append((record, manifest.parent / name))
    return records


def _json_for_html(value: Any) -> str:
    """Encode JSON without allowing HTML script termination."""
    return (
        json.dumps(value, ensure_ascii=True)
        .replace("&", r"\u0026")
        .replace("<", r"\u003c")
        .replace(">", r"\u003e")
    )


def build_review_page(root: Path, out_html: Path) -> int:
    """Write a self-contained, offline chip review page."""
    items = []
    for record, chip in _load_records(root):
        if record["status"] != "ok":
            continue
        with Image.open(chip) as image:
            width, height = image.size
        items.append(
            {
                "survey_id": record["survey_id"],
                "contact_id": record["contact_id"],
                "kind": record["kind"],
                "is_real": record["is_real"],
                "box_px": record["box_px"],
                "width": width,
                "height": height,
                "image": "data:image/png;base64,"
                + base64.b64encode(chip.read_bytes()).decode("ascii"),
            }
        )
    identities = [[item["survey_id"], item["contact_id"]] for item in items]
    digest = hashlib.sha256(json.dumps(identities).encode("utf-8")).hexdigest()
    payload = _json_for_html({"storage_key": f"netsight-noaa-review-v1-{digest}", "items": items})
    html = _PAGE.replace("__REVIEW_DATA__", payload)
    out_html.parent.mkdir(parents=True, exist_ok=True)
    out_html.write_text(html, encoding="utf-8")
    return len(items)


def _box(value: Any) -> list[float]:
    """Validate a finite, four-coordinate pixel box."""
    if not isinstance(value, list) or len(value) != 4:
        raise ValueError("A box must be a list of four finite numbers")
    if any(
        isinstance(number, bool)
        or not isinstance(number, (int, float))
        or not math.isfinite(number)
        for number in value
    ):
        raise ValueError("A box must be a list of four finite numbers")
    return [float(number) for number in value]


def apply_review(root: Path, review_json: Path, out_dir: Path) -> dict[str, int]:
    """Copy accepted chips and write clipped YOLO labels and a review manifest."""
    records = _load_records(root)
    sources = {(record["survey_id"], record["contact_id"]): record for record, _ in records}
    review = json.loads(review_json.read_text(encoding="utf-8"))
    if not isinstance(review, dict) or review.get("version") != 1:
        raise ValueError("Expected review version 1")
    entries = review.get("items")
    if not isinstance(entries, list):
        raise ValueError("Expected a review items list")

    decisions: dict[tuple[str, str], dict[str, Any]] = {}
    for entry in entries:
        identity = (entry["survey_id"], entry["contact_id"])
        if identity not in sources:
            raise ValueError(f"Unknown survey/contact id: {identity!r}")
        if identity in decisions:
            raise ValueError(f"Duplicate review item: {identity!r}")
        decision = entry.get("decision")
        if decision is not None and decision not in _DECISIONS:
            raise ValueError(f"Unknown decision: {decision!r}")
        if decision in ("keep", "move"):
            source = sources[identity]
            if source["status"] != "ok":
                raise ValueError(f"Cannot accept a chip with status {source['status']!r}")
            _box(source["box_px"] if decision == "keep" else entry.get("box_px"))
        decisions[identity] = entry

    counts = dict.fromkeys((*_DECISIONS, "undecided"), 0)
    output_manifest = []
    out_dir.mkdir(parents=True, exist_ok=True)
    for record, chip in records:
        identity = (record["survey_id"], record["contact_id"])
        entry = decisions.get(identity, {})
        decision = entry.get("decision")
        counts[decision if decision is not None else "undecided"] += 1
        result = dict(record)
        result["decision"] = decision
        result["reviewed_at"] = entry.get("reviewed_at")
        result["box_px"] = None
        if decision in ("keep", "move"):
            result["label_status"] = "reviewed by a person"
            coordinates = _box(record["box_px"] if decision == "keep" else entry["box_px"])
            with Image.open(chip) as image:
                width, height = image.size
            x0, y0, x1, y1 = coordinates
            x0, x1 = (max(0.0, min(float(width), x)) for x in (x0, x1))
            y0, y1 = (max(0.0, min(float(height), y)) for y in (y0, y1))
            result["box_px"] = [x0, y0, x1, y1]
            destination = out_dir / chip.name
            label = destination.with_suffix(".txt")
            if x1 - x0 < 2 or y1 - y0 < 2:
                # Remove stale exports when reapplying a review to the same directory.
                label.unlink(missing_ok=True)
                destination.unlink(missing_ok=True)
            else:
                if chip.resolve() != destination.resolve():
                    shutil.copyfile(chip, destination)
                values = (
                    (x0 + x1) / (2 * width),
                    (y0 + y1) / (2 * height),
                    (x1 - x0) / width,
                    (y1 - y0) / height,
                )
                label.write_text(
                    "0 " + " ".join(f"{value:.10g}" for value in values) + "\n",
                    encoding="utf-8",
                )
        else:
            destination = out_dir / chip.name
            destination.with_suffix(".txt").unlink(missing_ok=True)
            destination.unlink(missing_ok=True)
        output_manifest.append(result)

    (out_dir / "reviewed_manifest.json").write_text(
        json.dumps(output_manifest, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    return counts


_PAGE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>NetSight - check NOAA object boxes</title>
<style>
body { font: 16px system-ui, sans-serif; margin: 20px auto; max-width: 920px; padding: 0 16px; }
h1 { font-size: 24px; }
button { font: inherit; padding: 8px 12px; margin: 4px; cursor: pointer; }
button:focus-visible { outline: 3px solid #165bbb; }
#stage { position: relative; width: 512px; max-width: 100%; background: #222; }
#chip { display: block; width: 100%; height: auto; image-rendering: pixelated; }
#overlay { position: absolute; inset: 0; width: 100%; height: 100%; touch-action: none; }
#badge { display: inline-block; padding: 4px 12px; border-radius: 5px; background: #eee; }
#badge.keep { background: #bce8c8; }
#badge.move { background: #bfdcff; }
#badge.reject { background: #ffcbcb; }
#badge.unsure { background: #ffedac; }
#message { min-height: 1.5em; }
#pending { display: flex; flex-wrap: wrap; gap: 2px; }
#pending button { font-size: 14px; }
</style>
</head>
<body>
<h1>NetSight - check NOAA object boxes</h1>
<p>Look at the red box. Keep if an object is inside; Move if the object is nearby
(drag a new box on it); Reject if you see nothing.</p>
<p id="progress" aria-live="polite"></p>
<p id="details"></p>
<p><span id="badge"></span></p>
<div id="stage">
<img id="chip" alt="Side-scan sonar chip">
<canvas id="overlay" aria-label="Drag a new object box in Move mode"></canvas>
</div>
<div id="actions">
<button id="previous">← Previous</button>
<button id="keep">Keep (K)</button>
<button id="move">Move (M)</button>
<button id="save" disabled>Save box (Enter)</button>
<button id="reject">Reject (R)</button>
<button id="unsure">Unsure (U)</button>
<button id="next">Next →</button>
</div>
<p id="message" role="status"></p>
<p id="storage-warning" role="status"></p>
<button id="download">Download results</button>
<h2>Not done yet</h2>
<div id="pending"></div>
<script type="application/json" id="review-data">__REVIEW_DATA__</script>
<script>
"use strict";
const data = JSON.parse(document.getElementById("review-data").textContent);
const items = data.items;
const el = id => document.getElementById(id);
const canvas = el("overlay");
const ctx = canvas.getContext("2d");
const choices = new Set(["keep", "move", "reject", "unsure"]);
const validBox = b => Array.isArray(b) && b.length === 4 &&
    b.every(n => typeof n === "number" && Number.isFinite(n)) &&
    b[2] - b[0] >= 2 && b[3] - b[1] >= 2;
let answers = items.map(() => null);
let index = 0;
let moving = false;
let draft = null;
let start = null;
let pointerId = null;

try {
    const saved = JSON.parse(localStorage.getItem(data.storage_key) || "null");
    if (Array.isArray(saved) && saved.length === items.length) {
        answers = saved.map(a => {
            if (!a || !choices.has(a.decision) || typeof a.reviewed_at !== "string") return null;
            if (a.decision === "move" && !validBox(a.box_px)) return null;
            return a;
        });
    }
} catch {
    el("storage-warning").textContent =
        "Browser storage is unavailable. Download results before closing this page.";
}
const firstPending = answers.findIndex(a => a === null);
if (firstPending >= 0) index = firstPending;

function persist() {
    try {
        localStorage.setItem(data.storage_key, JSON.stringify(answers));
    } catch {
        el("storage-warning").textContent =
            "Could not save in this browser. Download results before closing this page.";
    }
}
function draw() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    if (!items.length) return;
    const answer = answers[index];
    const box = draft || (answer && answer.decision === "move" ?
        answer.box_px : items[index].box_px);
    ctx.strokeStyle = "#ff2020";
    ctx.lineWidth = 1.5;
    ctx.strokeRect(box[0], box[1], box[2] - box[0], box[3] - box[1]);
}
function show() {
    moving = false;
    draft = null;
    start = null;
    if (pointerId !== null && canvas.hasPointerCapture(pointerId)) {
        canvas.releasePointerCapture(pointerId);
    }
    pointerId = null;
    el("save").disabled = true;
    el("message").textContent = "";
    el("progress").textContent = `${answers.filter(Boolean).length} / ${items.length} done`;
    el("pending").replaceChildren();
    items.forEach((item, i) => {
        if (answers[i]) return;
        const button = document.createElement("button");
        button.textContent = `${i + 1}: ${item.survey_id} / ${item.contact_id}`;
        button.addEventListener("click", () => { index = i; show(); });
        el("pending").append(button);
    });
    if (!items.length) {
        el("details").textContent = "No chips with status ok were found.";
        el("stage").hidden = true;
        el("actions").hidden = true;
        el("badge").textContent = "No items";
        return;
    }
    const item = items[index];
    el("details").textContent =
        `${index + 1}. Survey: ${item.survey_id} | Contact: ${item.contact_id} | ` +
        `Kind: ${item.kind}` + (item.is_real === true ? " | confirmed real by NOAA" : "");
    const decision = answers[index]?.decision || "Not reviewed";
    el("badge").textContent = decision;
    el("badge").className = answers[index]?.decision || "";
    el("chip").src = item.image;
    canvas.width = item.width;
    canvas.height = item.height;
    el("previous").disabled = index === 0;
    el("next").disabled = index === items.length - 1;
    draw();
}
function navigate(delta) {
    if (!items.length) return;
    index = Math.max(0, Math.min(items.length - 1, index + delta));
    show();
}
function decide(decision) {
    if (!items.length) return;
    if (decision === "move" && !validBox(draft)) {
        el("message").textContent = "Draw a box at least 2 pixels wide and tall.";
        return;
    }
    answers[index] = {
        decision,
        box_px: decision === "keep" ? items[index].box_px :
            decision === "move" ? draft.slice() : null,
        reviewed_at: new Date().toISOString()
    };
    persist();
    navigate(1);
}
el("previous").onclick = () => navigate(-1);
el("next").onclick = () => navigate(1);
el("keep").onclick = () => decide("keep");
el("reject").onclick = () => decide("reject");
el("unsure").onclick = () => decide("unsure");
el("move").onclick = () => {
    if (!items.length) return;
    moving = true;
    draft = null;
    el("save").disabled = true;
    el("message").textContent = "Drag a new box around the object, then press Enter or Save box.";
    draw();
};
el("save").onclick = () => decide("move");
function point(event) {
    const rect = canvas.getBoundingClientRect();
    return [
        Math.max(0, Math.min(canvas.width, (event.clientX - rect.left) *
            canvas.width / rect.width)),
        Math.max(0, Math.min(canvas.height, (event.clientY - rect.top) *
            canvas.height / rect.height))
    ];
}
function updateDraft(event) {
    const end = point(event);
    draft = [
        Math.min(start[0], end[0]), Math.min(start[1], end[1]),
        Math.max(start[0], end[0]), Math.max(start[1], end[1])
    ];
    el("save").disabled = !validBox(draft);
    draw();
}
canvas.addEventListener("pointerdown", event => {
    if (!moving || pointerId !== null || event.button !== 0) return;
    event.preventDefault();
    pointerId = event.pointerId;
    start = point(event);
    canvas.setPointerCapture(pointerId);
    updateDraft(event);
});
canvas.addEventListener("pointermove", event => {
    if (start && event.pointerId === pointerId) updateDraft(event);
});
canvas.addEventListener("pointerup", event => {
    if (!start || event.pointerId !== pointerId) return;
    updateDraft(event);
    start = null;
    canvas.releasePointerCapture(pointerId);
    pointerId = null;
});
canvas.addEventListener("pointercancel", () => {
    start = null;
    pointerId = null;
    draft = null;
    el("save").disabled = true;
    draw();
});
document.addEventListener("keydown", event => {
    if (event.ctrlKey || event.metaKey || event.altKey || event.repeat) return;
    const actions = {
        k: () => decide("keep"),
        m: () => el("move").click(),
        r: () => decide("reject"),
        u: () => decide("unsure"),
        ArrowLeft: () => navigate(-1),
        ArrowRight: () => navigate(1),
        Enter: () => { if (moving && !start) decide("move"); }
    };
    const action = actions[event.key.length === 1 ? event.key.toLowerCase() : event.key];
    if (action) {
        event.preventDefault();
        action();
    }
});
el("download").onclick = () => {
    const result = {
        version: 1,
        items: items.map((item, i) => ({
            survey_id: item.survey_id,
            contact_id: item.contact_id,
            decision: answers[i]?.decision ?? null,
            box_px: answers[i]?.decision === "keep" ? item.box_px :
                answers[i]?.decision === "move" ? answers[i].box_px : null,
            reviewed_at: answers[i]?.reviewed_at ?? null
        }))
    };
    const blob = new Blob([JSON.stringify(result, null, 2)], {type: "application/json"});
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "noaa_review.json";
    document.body.append(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
};
show();
</script>
</body>
</html>
"""


def main() -> None:
    """Run the review builder or review applier."""
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    build = commands.add_parser("build", help="Build an offline review HTML file")
    build.add_argument("--root", type=Path, required=True)
    build.add_argument("--out", type=Path, required=True)
    apply = commands.add_parser("apply", help="Export reviewed chips and YOLO labels")
    apply.add_argument("--root", type=Path, required=True)
    apply.add_argument("--review", type=Path, required=True)
    apply.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "build":
        count = build_review_page(args.root, args.out)
        print(f"Built {args.out}: {count} items")
    else:
        counts = apply_review(args.root, args.review, args.out)
        summary = ", ".join(f"{key}={value}" for key, value in counts.items())
        print(f"Applied review to {args.out}: {summary}")


if __name__ == "__main__":
    main()
