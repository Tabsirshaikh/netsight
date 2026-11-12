"""Freeze NetSight benchmark v0: split manifest, NOAA outcome table and result tables.

Writes a self-contained folder that others can use to score their own detector the same way:
which survey recordings are train/val/test per dataset (by group, so no recording is split),
the CC0 NOAA contact-outcome table, and NetSight v0.4's numbers on the same protocol.

    python -m netsight.benchmark --out benchmark_v0
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
from collections import Counter
from pathlib import Path


def split_manifest(splits: dict) -> dict:
    """Per split and dataset: groups (recordings/sites), image count, object count, and a
    hash of the sorted image list so changes are detectable."""
    out: dict = {}
    for split, sets in splits.items():
        for name, samples in sets.items():
            members = sorted(f"{s.dataset_id}:{s.member}" for s in samples)
            groups = Counter(str(s.group) for s in samples)
            out.setdefault(name, {})[split] = {
                "groups": dict(sorted(groups.items())),
                "images": len(samples),
                "objects": int(sum(len(s.boxes) for s in samples)),
                "image_list_sha256": hashlib.sha256("\n".join(members).encode()).hexdigest(),
            }
    return out


def write_benchmark(root: Path, out: Path) -> Path:
    from netsight.detect.pilot import build_splits

    out.mkdir(parents=True, exist_ok=True)
    splits = build_splits(root)
    (out / "splits.json").write_text(json.dumps(split_manifest(splits), indent=2), "utf-8")
    noaa = root / "processed" / "noaa"
    for name in ("features.csv", "contacts.csv", "summary.csv"):
        if (noaa / name).exists():
            shutil.copy2(noaa / name, out / f"noaa_{name}")
    results = {}
    for rel in (
        "runs/injection_v0.4/summary.json",
        "runs/injection_v0.4_s1/summary.json",
        "runs/withdrawal_v0.4.json",
        "runs/fusion_v0.4/results.json",
        "runs/onnx_v0.4/parity.json",
        "runs/operating_v0.4.json",
    ):
        p = root / rel
        if p.exists():
            results[rel] = json.loads(p.read_text("utf-8"))
    (out / "results_v0.4.json").write_text(json.dumps(results, indent=2, default=str), "utf-8")
    rows = []
    for rel in sorted(results):
        rows.append({"file": rel, "sha256": hashlib.sha256((root / rel).read_bytes()).hexdigest()})
    with (out / "result_files.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["file", "sha256"])
        w.writeheader()
        w.writerows(rows)
    return out


def main(argv: list[str] | None = None) -> int:
    from netsight.config import data_dir

    p = argparse.ArgumentParser()
    p.add_argument("--out", default="benchmark_v0")
    a = p.parse_args(argv)
    print(write_benchmark(data_dir(), data_dir() / a.out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
