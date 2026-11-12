"""Training manifest ("model label"): which data a model learned from, and whether it may ship.

A model is a *product* model only if every training dataset is in the commercial tier. Any
research_only dataset, or a conditional one whose terms are unresolved, makes it a *research*
model: fine for research, benchmarks and clearly labelled demos, never for sale.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Sequence
from datetime import UTC, datetime
from pathlib import Path

from netsight.trust.provenance import Ledger

NO_NOTICE_LICENCES = ("CC0", "PUBLIC DOMAIN", "PDDL")
RESEARCH_LABEL = "RESEARCH MODEL - trained on research-only or unresolved data; not for product use"
PRODUCT_LABEL = "PRODUCT MODEL - trained only on commercially licensed data"


class ResearchModelError(RuntimeError):
    """Raised when a research model is about to be released as a product."""


def _canonical(obj) -> str:
    return json.dumps(
        obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    )


def build_training_manifest(
    dataset_ids: Iterable[str],
    register: Sequence[dict],
    *,
    model_id: str,
    code_version: str,
    config: dict,
) -> dict:
    ids = list(dict.fromkeys(dataset_ids))
    if not ids:
        raise ValueError("a model must name at least one training dataset")
    entries = {e["id"]: e for e in register}
    unknown = [i for i in ids if i not in entries]
    if unknown:
        raise ValueError(f"datasets not in the licence register: {unknown}")
    datasets, blocking, notices = [], [], []
    for i in ids:
        e = entries[i]
        licence = str(e.get("licence", ""))
        datasets.append(
            {
                "id": i,
                "title": e.get("title", ""),
                "licence": licence,
                "tier": e["tier"],
                "commercial_use": str(e.get("commercial_use", "")),
            }
        )
        if e["tier"] != "commercial":
            blocking.append(i)
        if not licence.upper().startswith(NO_NOTICE_LICENCES):
            notices.append({"id": i, "title": e.get("title", ""), "licence": licence})
    model_class = "research" if blocking else "product"
    return {
        "model_id": model_id,
        "created": datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "model_class": model_class,
        "label": RESEARCH_LABEL if blocking else PRODUCT_LABEL,
        "blocking_datasets": blocking,
        "datasets": datasets,
        "notices_required": notices,
        "code_version": code_version,
        "config": config,
    }


def write_manifest(manifest: dict, out_dir: str | Path, *, ledger: Ledger | None = None) -> Path:
    """Write manifest.json (with its own sha256) and record it in the provenance ledger."""
    body = {k: v for k, v in manifest.items() if k != "manifest_sha256"}
    digest = hashlib.sha256(_canonical(body).encode("utf-8")).hexdigest()
    saved = {**body, "manifest_sha256": digest}
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    path = out / "manifest.json"
    path.write_text(json.dumps(saved, indent=2, ensure_ascii=False), encoding="utf-8")
    if ledger is not None:
        ledger.append(
            "model",
            {
                "model_id": saved["model_id"],
                "model_class": saved["model_class"],
                "datasets": [d["id"] for d in saved["datasets"]],
                "blocking_datasets": saved["blocking_datasets"],
                "manifest_sha256": digest,
            },
        )
    return path


def assert_product_release(manifest: dict) -> None:
    if manifest.get("model_class") != "product":
        blocked = ", ".join(manifest.get("blocking_datasets", [])) or "unknown"
        raise ResearchModelError(
            f"{manifest.get('model_id')} is a research model (trained on: {blocked}); "
            "retrain on commercial-tier data or obtain licences before release"
        )


def inherited_dataset_ids(own: Iterable[str], base_model_dir: str | Path | None) -> list[str]:
    """A fine-tuned model inherits every dataset its starting model learned from.

    Fine-tuning a research model on clean data does not make it a product model: the base
    model's manifest datasets are added after the model's own (duplicates removed).
    """
    ids = list(dict.fromkeys(own))
    if base_model_dir is not None:
        path = Path(base_model_dir) / "manifest.json"
        if path.exists():
            base = json.loads(path.read_text(encoding="utf-8"))
            ids += [d["id"] for d in base.get("datasets", []) if d["id"] not in ids]
    return ids
