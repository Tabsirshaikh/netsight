"""Deterministic, covariance-gated association across sonar passes."""

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
