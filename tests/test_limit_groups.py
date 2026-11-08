from types import SimpleNamespace

from netsight.detect.pilot import limit_groups


def _s(ds, g):
    return SimpleNamespace(dataset_id=ds, group=g)


def test_limit_groups_is_nested_and_per_dataset():
    samples = [_s("a", f"r{i}") for i in range(10) for _ in range(3)] + [_s("b", "x"), _s("b", "y")]
    small = {s.group for s in limit_groups(samples, 2, seed=1) if s.dataset_id == "a"}
    big = {s.group for s in limit_groups(samples, 5, seed=1) if s.dataset_id == "a"}
    assert len(small) == 2 and len(big) == 5 and small <= big
    assert len([s for s in limit_groups(samples, 2, seed=1) if s.group in small]) == 6
    assert {s.group for s in limit_groups(samples, 1, seed=1) if s.dataset_id == "b"} <= {"x", "y"}
