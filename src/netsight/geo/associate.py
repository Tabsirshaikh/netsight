"""Deterministic, covariance-gated association across sonar passes.

``associate_passes`` is the plan's method (section 8.5): passes in order, each matched to the
existing objects by Hungarian assignment on a cost of Mahalanobis d2 (hard gate) plus soft
class and size costs, with persistent object IDs and an append-only history. ``associate``
is the earlier greedy pair-merging baseline, kept for comparison.
"""

from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from math import isfinite

import numpy as np


@dataclass(frozen=True)
class Contact:
    """A contact in a common local east/north coordinate frame."""

    contact_id: str
    pass_id: str
    east_m: float
    north_m: float
    cov: tuple[float, float, float]
    p_real: float
    label: str | None = None  # class, when known (soft association cost)
    size_m: float | None = None  # object length in metres, when known (soft association cost)


@dataclass(frozen=True)
class TrackedObject:
    """A fused contact cluster with at most one contact from each pass."""

    object_id: str
    members: tuple[str, ...]
    east_m: float
    north_m: float
    cov: tuple[float, float, float]
    passes: tuple[str, ...]
    best_d2: float


def associate(contacts: Sequence[Contact], *, gate_d2: float = 9.21) -> list[TrackedObject]:
    """Greedily merge eligible contact pairs, using their original covariances.

    Pair ties use lexically sorted contact IDs. Object numbering and member
    ordering instead follow input order. ``p_real`` is validated but does not
    alter either the gate or inverse-covariance fusion.
    """
    if not isfinite(gate_d2) or gate_d2 < 0:
        raise ValueError("gate_d2 must be finite and non-negative")
    contacts = tuple(contacts)
    ids = [contact.contact_id for contact in contacts]
    if len(set(ids)) != len(ids):
        raise ValueError("duplicate contact_id")

    covariances = []
    positions = []
    for contact in contacts:
        if len(contact.cov) != 3:
            raise ValueError(f"contact {contact.contact_id!r} covariance must have three entries")
        ve, vn, cen = contact.cov
        covariance = np.array([[ve, cen], [cen, vn]], dtype=float)
        position = np.array([contact.east_m, contact.north_m], dtype=float)
        if not np.isfinite(position).all() or not np.isfinite(covariance).all():
            raise ValueError(
                f"contact {contact.contact_id!r} position and covariance must be finite"
            )
        if np.any(np.linalg.eigvalsh(covariance) <= 0):
            raise ValueError(f"contact {contact.contact_id!r} covariance must be positive definite")
        if not isfinite(contact.p_real) or not 0 <= contact.p_real <= 1:
            raise ValueError(f"contact {contact.contact_id!r} p_real must be between 0 and 1")
        positions.append(position)
        covariances.append(covariance)

    pairs: list[tuple[float, str, str, int, int]] = []
    for i, first in enumerate(contacts):
        for j in range(i + 1, len(contacts)):
            second = contacts[j]
            if first.pass_id == second.pass_id:
                continue
            delta = positions[i] - positions[j]
            d2 = float(delta @ np.linalg.solve(covariances[i] + covariances[j], delta))
            if d2 <= gate_d2:
                id_a, id_b = sorted((first.contact_id, second.contact_id))
                pairs.append((d2, id_a, id_b, i, j))
    pairs.sort()

    parent = list(range(len(contacts)))
    passes = [{contact.pass_id} for contact in contacts]
    best = [float("inf")] * len(contacts)

    def find(index: int) -> int:
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    for d2, _, _, i, j in pairs:
        a, b = find(i), find(j)
        if a == b or passes[a] & passes[b]:
            continue
        a, b = min(a, b), max(a, b)
        parent[b] = a
        passes[a].update(passes[b])
        best[a] = min(best[a], best[b], d2)

    groups: dict[int, list[int]] = {}
    for i in range(len(contacts)):
        groups.setdefault(find(i), []).append(i)

    objects = []
    for number, (root, indices) in enumerate(groups.items(), start=1):
        if len(indices) == 1:
            index = indices[0]
            mean = positions[index]
            covariance = covariances[index]
        else:
            precision = np.zeros((2, 2))
            weighted_position = np.zeros(2)
            for index in indices:
                inverse = np.linalg.inv(covariances[index])
                precision += inverse
                weighted_position += inverse @ positions[index]
            covariance = np.linalg.inv(precision)
            mean = covariance @ weighted_position
        objects.append(
            TrackedObject(
                object_id=f"OBJ-{number:04d}",
                members=tuple(contacts[index].contact_id for index in indices),
                east_m=float(mean[0]),
                north_m=float(mean[1]),
                cov=(
                    float(covariance[0, 0]),
                    float(covariance[1, 1]),
                    float(covariance[0, 1]),
                ),
                passes=tuple(sorted(passes[root])),
                best_d2=0.0 if len(indices) == 1 else best[root],
            )
        )
    return objects


def mis_association_rate(
    objects: Sequence[TrackedObject], truth: Mapping[str, str]
) -> dict[str, int | float]:
    """Count unordered-pair association errors.

    The truth mapping defines the evaluation population. Truth contacts absent
    from the objects have no predicted links. Every predicted member must have
    truth, and a contact may occur in only one predicted object.
    """

    def pair_count(count: int) -> int:
        return count * (count - 1) // 2

    true_pairs = sum(pair_count(count) for count in Counter(truth.values()).values())
    predicted_pairs = 0
    correct_pairs = 0
    seen: set[str] = set()
    for obj in objects:
        labels: Counter[str] = Counter()
        for member in obj.members:
            if member in seen:
                raise ValueError(f"duplicate predicted contact_id {member!r}")
            if member not in truth:
                raise ValueError(f"missing truth for contact_id {member!r}")
            seen.add(member)
            labels[truth[member]] += 1
        predicted_pairs += pair_count(len(obj.members))
        correct_pairs += sum(pair_count(count) for count in labels.values())

    false_merges = predicted_pairs - correct_pairs
    missed_merges = true_pairs - correct_pairs
    return {
        "true_pairs": true_pairs,
        "predicted_pairs": predicted_pairs,
        "false_merges": false_merges,
        "missed_merges": missed_merges,
        "rate": (false_merges + missed_merges) / max(1, true_pairs + false_merges),
    }


CLASS_MISMATCH_COST = 4.0  # added when both classes are known and differ
SIZE_COST_PER_DOUBLING = 1.0  # times (log2 size ratio)^2, when both sizes are known


@dataclass(frozen=True)
class AssociationResult:
    objects: list[TrackedObject]
    history: list[dict]  # append-only: create / match events in processing order


def _cov(x: Contact) -> np.ndarray:
    return np.array([[x.cov[0], x.cov[2]], [x.cov[2], x.cov[1]]], dtype=float)


def _validate(contacts: Sequence[Contact]) -> None:
    ids = [x.contact_id for x in contacts]
    if len(set(ids)) != len(ids):
        raise ValueError("duplicate contact_id")
    for x in contacts:
        if len(x.cov) != 3:
            raise ValueError(f"contact {x.contact_id!r} covariance must have three entries")
        cov = _cov(x)
        if not (np.isfinite([x.east_m, x.north_m]).all() and np.isfinite(cov).all()):
            raise ValueError(f"contact {x.contact_id!r} position and covariance must be finite")
        if np.any(np.linalg.eigvalsh(cov) <= 0):
            raise ValueError(f"contact {x.contact_id!r} covariance must be positive definite")
        if not isfinite(x.p_real) or not 0 <= x.p_real <= 1:
            raise ValueError(f"contact {x.contact_id!r} p_real must be between 0 and 1")
        if x.size_m is not None and not (isfinite(x.size_m) and x.size_m > 0):
            raise ValueError(f"contact {x.contact_id!r} size_m must be > 0")


class _Track:
    def __init__(self, object_id: str) -> None:
        self.id = object_id
        self.info = np.zeros((2, 2))
        self.wpos = np.zeros(2)
        self.members: list[Contact] = []
        self.best = float("inf")

    def add(self, x: Contact) -> None:
        info = np.linalg.inv(_cov(x))
        self.info = self.info + info
        self.wpos = self.wpos + info @ np.array([x.east_m, x.north_m])
        self.members.append(x)

    def state(self) -> tuple[np.ndarray, np.ndarray]:
        cov = np.linalg.inv(self.info)
        return cov @ self.wpos, cov


def associate_passes(
    contacts: Sequence[Contact],
    *,
    gate_d2: float = 9.21,
    class_cost: float = CLASS_MISMATCH_COST,
    size_cost: float = SIZE_COST_PER_DOUBLING,
) -> AssociationResult:
    """Associate contacts pass by pass (passes in order of first appearance).

    Each pass is matched to the current objects by Hungarian assignment. A pair is allowed
    only when d2 = delta' (cov_object + cov_contact)^-1 delta <= ``gate_d2``; its cost is d2
    plus the soft class and size costs. Leaving an object or a contact unmatched costs
    ``gate_d2 / 2`` each, so a pair is taken only when its total cost is at most ``gate_d2``.
    Objects keep their IDs when later passes are added; unmatched contacts create new objects.
    """
    from scipy.optimize import linear_sum_assignment

    if not isfinite(gate_d2) or gate_d2 < 0:
        raise ValueError("gate_d2 must be finite and non-negative")
    contacts = tuple(contacts)
    _validate(contacts)
    order: list[str] = []
    for x in contacts:
        if x.pass_id not in order:
            order.append(x.pass_id)

    tracks: list[_Track] = []
    history: list[dict] = []

    def log(event: str, x: Contact, track: _Track, d2: float | None, cost: float | None) -> None:
        history.append(
            {
                "seq": len(history),
                "event": event,
                "object_id": track.id,
                "contact_id": x.contact_id,
                "pass_id": x.pass_id,
                "d2": d2,
                "cost": cost,
            }
        )

    big = 1e9
    for pass_id in order:
        new = [x for x in contacts if x.pass_id == pass_id]
        n, m = len(tracks), len(new)
        cost = np.full((n + m, m + n), big)
        d2s = np.full((n, m), np.inf)
        for i, track in enumerate(tracks):
            mean, cov_t = track.state()
            labels = {y.label for y in track.members if y.label is not None}
            sizes = [y.size_m for y in track.members if y.size_m is not None]
            for j, x in enumerate(new):
                delta = mean - np.array([x.east_m, x.north_m])
                d2 = float(delta @ np.linalg.solve(cov_t + _cov(x), delta))
                d2s[i, j] = d2
                if d2 > gate_d2:
                    continue
                total = d2
                if x.label is not None and labels and x.label not in labels:
                    total += class_cost
                if x.size_m is not None and sizes:
                    total += size_cost * float(np.log2(x.size_m / float(np.mean(sizes)))) ** 2
                cost[i, j] = total
        for i in range(n):
            cost[i, m + i] = gate_d2 / 2  # object not seen on this pass
        for j in range(m):
            cost[n + j, j] = gate_d2 / 2  # contact starts a new object
        cost[n:, m:] = 0.0
        rows, cols = linear_sum_assignment(cost)
        matched = {
            int(col): int(r)
            for r, col in zip(rows, cols, strict=True)
            if r < n and col < m and cost[r, col] < big
        }
        for j, x in enumerate(new):
            if j in matched:
                i = matched[j]
                track = tracks[i]
                track.best = min(track.best, float(d2s[i, j]))
                track.add(x)
                log("match", x, track, float(d2s[i, j]), float(cost[i, j]))
            else:
                track = _Track(f"OBJ-{len(tracks) + 1:04d}")
                track.add(x)
                tracks.append(track)
                log("create", x, track, None, None)

    objects = []
    for track in tracks:
        mean, cov = track.state()
        objects.append(
            TrackedObject(
                object_id=track.id,
                members=tuple(x.contact_id for x in track.members),
                east_m=float(mean[0]),
                north_m=float(mean[1]),
                cov=(float(cov[0, 0]), float(cov[1, 1]), float(cov[0, 1])),
                passes=tuple(sorted({x.pass_id for x in track.members})),
                best_d2=0.0 if len(track.members) == 1 else track.best,
            )
        )
    return AssociationResult(objects=objects, history=history)
