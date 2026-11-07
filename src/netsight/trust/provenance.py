"""Append-only, hash-chained provenance ledger (one JSON object per line).

Every entry stores the hash of the previous entry, so editing, deleting or reordering any
line is detected by `verify()`. Expert reviews ("review") and physical verifications by diver,
ROV, clearance or retrieval ("verification") are separate kinds and are never merged.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

GENESIS = "0" * 64
KINDS = frozenset(
    {"data", "model", "calibrator", "run", "contact", "review", "verification", "report"}
)


def _utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def _canonical(obj) -> str:
    try:
        return json.dumps(
            obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
        )
    except (TypeError, ValueError) as exc:
        raise ValueError(f"payload is not strict JSON: {exc}") from exc


def _entry_hash(entry: dict) -> str:
    body = {k: entry[k] for k in ("seq", "kind", "time", "prev_hash", "payload")}
    return hashlib.sha256(_canonical(body).encode("utf-8")).hexdigest()


class Ledger:
    def __init__(self, path: str | Path, *, clock: Callable[[], str] = _utc_now) -> None:
        self.path = Path(path)
        self._clock = clock
        entries = self._read(strict=False)
        self.head = entries[-1]["hash"] if entries else GENESIS
        self._next_seq = entries[-1]["seq"] + 1 if entries else 0

    def _read(self, *, strict: bool) -> list[dict]:
        if not self.path.exists():
            return []
        out = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                if strict:
                    raise
        return out

    def entries(self) -> list[dict]:
        return self._read(strict=True)

    def append(self, kind: str, payload: dict) -> str:
        """Add one entry and return its hash. Nothing is written if validation fails."""
        if kind not in KINDS:
            raise ValueError(f"unknown entry kind {kind!r}; expected one of {sorted(KINDS)}")
        if not isinstance(payload, dict):
            raise ValueError("payload must be a dict")
        entry = {
            "seq": self._next_seq,
            "kind": kind,
            "time": self._clock(),
            "prev_hash": self.head,
            "payload": payload,
        }
        entry["hash"] = _entry_hash(entry)  # raises ValueError on non-JSON payloads
        line = _canonical(entry)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "a", encoding="utf-8", newline="\n") as f:
            f.write(line + "\n")
        self.head = entry["hash"]
        self._next_seq += 1
        return entry["hash"]

    def verify(self) -> list[str]:
        """Problems found in the chain; an empty list means the ledger is intact."""
        problems: list[str] = []
        if not self.path.exists():
            return problems
        expected_prev = GENESIS
        index = 0
        for n, line in enumerate(self.path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            try:
                entry = json.loads(line)
                seq = entry["seq"]
                recomputed = _entry_hash(entry)
            except (json.JSONDecodeError, KeyError, ValueError, TypeError) as exc:
                problems.append(f"line {n}: unreadable entry ({exc})")
                index += 1
                continue
            if seq != index:
                problems.append(f"seq {seq}: expected seq {index} (entry missing or reordered)")
            if recomputed != entry.get("hash"):
                problems.append(f"seq {seq}: hash mismatch (entry edited)")
            if entry["prev_hash"] != expected_prev:
                problems.append(f"seq {seq}: prev_hash does not match the previous entry")
            expected_prev = entry.get("hash", "")
            index += 1
        return problems
