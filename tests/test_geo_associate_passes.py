"""Plan 8.5 association: Hungarian per pass, soft class/size costs, persistent IDs, history."""

import pytest

from netsight.geo.associate import Contact, associate, associate_passes, mis_association_rate


def c(cid, pass_id, east=0.0, north=0.0, label=None, size=None, cov=(1.0, 1.0, 0.0)):
    return Contact(cid, pass_id, east, north, cov, 0.8, label=label, size_m=size)


def test_hungarian_finds_both_matches_where_greedy_takes_the_closest_pair_first():
    # a1-b1 is the closest pair, but taking it leaves a2 and b2 with nothing in the gate.
    # The optimal assignment a1-b2, a2-b1 keeps every contact matched.
    inputs = [
        c("a1", "p1", east=0.0),
        c("a2", "p1", east=-3.0),
        c("b1", "p2", east=-1.0),
        c("b2", "p2", east=2.0),
    ]
    truth = {"a1": "T1", "b2": "T1", "a2": "T2", "b1": "T2"}
    greedy = associate(inputs, gate_d2=9.21)
    hungarian = associate_passes(inputs, gate_d2=9.21).objects
    assert mis_association_rate(greedy, truth)["rate"] > 0
    assert mis_association_rate(hungarian, truth)["rate"] == 0
    assert sorted(o.members for o in hungarian) == [("a1", "b2"), ("a2", "b1")]


def test_class_mismatch_is_a_soft_cost():
    near = [c("a", "p1", label="net"), c("b", "p2", east=0.5, label="tyre")]
    far = [c("a", "p1", label="net"), c("b", "p2", east=3.5, label="tyre")]  # d2 = 6.125
    assert len(associate_passes(near).objects) == 1  # close enough despite the class
    assert len(associate_passes(far).objects) == 2  # 6.125 + 4 (class) > gate 9.21
    same = [c("a", "p1", label="net"), c("b", "p2", east=3.5, label="net")]
    assert len(associate_passes(same).objects) == 1
    unknown = [c("a", "p1", label="net"), c("b", "p2", east=3.5, label=None)]
    assert len(associate_passes(unknown).objects) == 1  # unknown class costs nothing


def test_size_ratio_is_a_soft_cost():
    alike = [c("a", "p1", size=2.0), c("b", "p2", east=2.0, size=2.2)]
    unlike = [c("a", "p1", size=0.5), c("b", "p2", east=2.0, size=8.0)]  # 4 doublings
    assert len(associate_passes(alike).objects) == 1
    assert len(associate_passes(unlike).objects) == 2


def test_ids_persist_when_a_later_pass_is_added_and_history_is_append_only():
    first = [c("a", "p1"), c("b", "p1", east=30.0), c("x", "p2", east=0.5)]
    r1 = associate_passes(first)
    r2 = associate_passes([*first, c("y", "p3", east=30.4), c("z", "p3", east=90.0)])
    ids1 = {o.members[0]: o.object_id for o in r1.objects}
    ids2 = {o.members[0]: o.object_id for o in r2.objects}
    assert ids2["a"] == ids1["a"] and ids2["b"] == ids1["b"]
    assert r2.history[: len(r1.history)] == r1.history
    events = [(e["event"], e["contact_id"], e["object_id"]) for e in r2.history]
    assert ("match", "y", ids1["b"]) in events and ("create", "z", "OBJ-0003") in events
    assert [e["seq"] for e in r2.history] == list(range(len(r2.history)))


def test_two_pass_fusion_matches_inverse_covariance_mean():
    obj = associate_passes(
        [c("a", "p1", cov=(4.0, 4.0, 0.0)), c("b", "p2", east=1.0, cov=(4.0, 4.0, 0.0))]
    ).objects[0]
    assert (obj.east_m, obj.north_m) == pytest.approx((0.5, 0.0))
    assert obj.cov == pytest.approx((2.0, 2.0, 0.0))
    assert obj.best_d2 == pytest.approx(1.0 / 8.0)


def test_same_pass_never_merges():
    assert len(associate_passes([c("a", "p1"), c("b", "p1")]).objects) == 2
