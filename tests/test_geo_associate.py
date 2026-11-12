"""Hand-computed gating, fusion, and pairwise association-error tests."""

from dataclasses import FrozenInstanceError, replace

import numpy as np
import pytest

from netsight.geo.associate import Contact, TrackedObject, associate, mis_association_rate


def contact(contact_id, pass_id, east=0.0, north=0.0, cov=(4.0, 4.0, 0.0)):
    """Create a contact with two-metre isotropic standard deviation by default."""
    return Contact(contact_id, pass_id, east, north, cov, 0.8)


def tracked(object_id, members):
    """Build an evaluation-only object with no fabricated position."""
    nan = float("nan")
    return TrackedObject(object_id, tuple(members), nan, nan, (nan, nan, nan), (), 0.0)


def test_two_pass_merge_uses_summed_covariance():
    objects = associate([contact("a", "p1"), contact("b", "p2", east=1.0)])
    assert len(objects) == 1
    obj = objects[0]
    assert obj.object_id == "OBJ-0001"
    assert obj.members == ("a", "b")
    assert obj.passes == ("p1", "p2")
    assert (obj.east_m, obj.north_m) == pytest.approx((0.5, 0.0))
    assert obj.cov == pytest.approx((2.0, 2.0, 0.0))
    assert obj.best_d2 == pytest.approx(1.0 / (4.0 + 4.0))


def test_gate_boundary_is_inclusive():
    inputs = [contact("a", "p1"), contact("b", "p2", east=1.0)]
    assert len(associate(inputs, gate_d2=0.125)) == 1
    assert len(associate(inputs, gate_d2=0.124)) == 2


def test_same_pass_never_merges_even_when_coincident():
    inputs = [contact("a", "p1"), contact("b", "p1")]
    objects = associate(inputs)
    assert [obj.members for obj in objects] == [("a",), ("b",)]
    assert [obj.best_d2 for obj in objects] == [0.0, 0.0]
    assert objects[0].cov == (4.0, 4.0, 0.0)


def test_distant_contacts_remain_separate():
    # d2=50^2/(4+4)=312.5, above the default gate.
    objects = associate([contact("a", "p1"), contact("b", "p2", east=50.0)])
    assert [obj.members for obj in objects] == [("a",), ("b",)]
    assert [obj.east_m for obj in objects] == [0.0, 50.0]
    assert [obj.object_id for obj in objects] == ["OBJ-0001", "OBJ-0002"]


def test_anisotropic_inverse_covariance_weighted_mean():
    # East precisions are 1/4 and 1; north precisions are 1 and 1/4.
    # Means: (10/1.25, 2.5/1.25)=(8,2); both variances=1/1.25.
    inputs = [
        contact("a", "p2", cov=(4.0, 1.0, 0.0)),
        contact("b", "p1", east=10.0, north=10.0, cov=(1.0, 4.0, 0.0)),
    ]
    obj = associate(inputs, gate_d2=40.0)[0]
    assert obj.members == ("a", "b")
    assert obj.passes == ("p1", "p2")
    assert (obj.east_m, obj.north_m) == pytest.approx((8.0, 2.0))
    assert obj.cov == pytest.approx((0.8, 0.8, 0.0))
    assert obj.best_d2 == pytest.approx(100.0 / 5.0 + 100.0 / 5.0)


def test_correlated_covariance_is_retained():
    inputs = [
        contact("a", "p1", cov=(2.0, 2.0, 1.0)),
        contact("b", "p2", east=2.0, north=2.0, cov=(2.0, 2.0, 1.0)),
    ]
    obj = associate(inputs)[0]
    assert (obj.east_m, obj.north_m) == pytest.approx((1.0, 1.0))
    assert obj.cov == pytest.approx((1.0, 1.0, 0.5))
    # Sum covariance [[4,2],[2,4]] has inverse [[4,-2],[-2,4]]/12.
    assert obj.best_d2 == pytest.approx(4.0 / 3.0)


def test_three_pass_cluster_best_distance_and_fusion():
    objects = associate(
        [contact("c", "p3", east=0.0), contact("a", "p1", east=1.0), contact("b", "p2", east=2.0)]
    )
    assert len(objects) == 1
    obj = objects[0]
    assert obj.members == ("c", "a", "b")
    assert obj.passes == ("p1", "p2", "p3")
    assert (obj.east_m, obj.north_m) == pytest.approx((1.0, 0.0))
    assert obj.cov == pytest.approx((4.0 / 3.0, 4.0 / 3.0, 0.0))
    assert obj.best_d2 == pytest.approx(0.125)


def test_cluster_pass_conflict_blocks_transitive_merge():
    # AB has d2=1/2; BC has d2=4/2. Once AB merges, C conflicts with A's pass.
    inputs = [
        contact("a", "p1", cov=(1.0, 1.0, 0.0)),
        contact("b", "p2", east=1.0, cov=(1.0, 1.0, 0.0)),
        contact("c", "p1", east=3.0, cov=(1.0, 1.0, 0.0)),
    ]
    objects = associate(inputs)
    assert [obj.members for obj in objects] == [("a", "b"), ("c",)]
    assert objects[0].best_d2 == 0.5


def test_ties_use_ids_but_objects_and_members_use_input_order():
    # Both eligible distances are 1/8. Pair (a,b) precedes (b,z).
    inputs = [
        contact("z", "p1"),
        contact("b", "p2", east=1.0),
        contact("a", "p1", east=2.0),
    ]
    objects = associate(inputs)
    assert [obj.object_id for obj in objects] == ["OBJ-0001", "OBJ-0002"]
    assert [obj.members for obj in objects] == [("z",), ("b", "a")]
    assert objects[1].east_m == pytest.approx(1.5)
    assert associate(inputs) == objects


def test_probability_does_not_change_fusion():
    inputs = [contact("a", "p1"), contact("b", "p2", east=1.0)]
    changed = [replace(inputs[0], p_real=0.0), replace(inputs[1], p_real=1.0)]
    assert associate(inputs) == associate(changed)


def test_empty_input_and_frozen_records():
    assert associate([]) == []
    item = contact("a", "p1")
    with pytest.raises(FrozenInstanceError):
        item.east_m = 1.0
    obj = associate([item])[0]
    with pytest.raises(FrozenInstanceError):
        obj.east_m = 1.0


def test_duplicate_ids_rejected():
    with pytest.raises(ValueError, match="duplicate contact_id"):
        associate([contact("a", "p1"), contact("a", "p2")])


@pytest.mark.parametrize("gate", [-1.0, np.nan, np.inf])
def test_invalid_gate(gate):
    with pytest.raises(ValueError, match="gate_d2"):
        associate([], gate_d2=gate)


@pytest.mark.parametrize(
    "changes",
    [
        {"east_m": np.nan},
        {"north_m": np.inf},
        {"cov": (0.0, 1.0, 0.0)},
        {"cov": (-1.0, 1.0, 0.0)},
        {"cov": (1.0, 1.0, 2.0)},
        {"cov": (np.nan, 1.0, 0.0)},
        {"cov": (1.0, 1.0)},
        {"p_real": -0.1},
        {"p_real": 1.1},
        {"p_real": np.nan},
    ],
)
def test_invalid_contact(changes):
    with pytest.raises(ValueError, match=".+"):
        associate([replace(contact("a", "p1"), **changes)])


def test_mis_association_hand_case():
    # Truth pairs: ab, ac, bc, de. Predicted pairs: ab, ad, bd.
    # Only ab is correct: two false merges, three missed merges, rate=5/6.
    truth = {"a": "T1", "b": "T1", "c": "T1", "d": "T2", "e": "T2"}
    objects = [
        tracked("OBJ-0001", ("a", "b", "d")),
        tracked("OBJ-0002", ("c",)),
        tracked("OBJ-0003", ("e",)),
    ]
    assert mis_association_rate(objects, truth) == {
        "true_pairs": 4,
        "predicted_pairs": 3,
        "false_merges": 2,
        "missed_merges": 3,
        "rate": 5.0 / 6.0,
    }


def test_mis_association_perfect_empty_and_missing_predictions():
    truth = {"a": "T1", "b": "T1", "c": "T2"}
    perfect = [tracked("OBJ-0001", ("b", "a")), tracked("OBJ-0002", ("c",))]
    assert mis_association_rate(perfect, truth) == {
        "true_pairs": 1,
        "predicted_pairs": 1,
        "false_merges": 0,
        "missed_merges": 0,
        "rate": 0.0,
    }
    assert mis_association_rate([], {}) == {
        "true_pairs": 0,
        "predicted_pairs": 0,
        "false_merges": 0,
        "missed_merges": 0,
        "rate": 0.0,
    }
    assert mis_association_rate([], truth) == {
        "true_pairs": 1,
        "predicted_pairs": 0,
        "false_merges": 0,
        "missed_merges": 1,
        "rate": 1.0,
    }


def test_false_merge_without_true_pairs():
    result = mis_association_rate([tracked("OBJ-0001", ("a", "b"))], {"a": "T1", "b": "T2"})
    assert result == {
        "true_pairs": 0,
        "predicted_pairs": 1,
        "false_merges": 1,
        "missed_merges": 0,
        "rate": 1.0,
    }


def test_invalid_evaluation_membership():
    with pytest.raises(ValueError, match="missing truth"):
        mis_association_rate([tracked("OBJ-0001", ("a",))], {})
    with pytest.raises(ValueError, match="duplicate"):
        mis_association_rate(
            [tracked("OBJ-0001", ("a",)), tracked("OBJ-0002", ("a",))], {"a": "T1"}
        )
    with pytest.raises(ValueError, match="duplicate"):
        mis_association_rate([tracked("OBJ-0001", ("a", "a"))], {"a": "T1"})
