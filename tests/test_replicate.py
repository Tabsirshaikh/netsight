import numpy as np

from netsight.datasets.detection import DetectionSample
from netsight.detect.replicate import random_image_split


def _samples(n):
    return [
        DetectionSample(
            "mine", "z.zip", f"{i:04d}.jpg", 10, 10, np.zeros((0, 4)), [], f"{2010 + i % 5}"
        )
        for i in range(n)
    ]


def test_random_split_ignores_groups_and_is_reproducible():
    s = _samples(100)
    a = random_image_split(s, test_fraction=0.2, val_fraction=0.1, seed=7)
    b = random_image_split(s, test_fraction=0.2, val_fraction=0.1, seed=7)
    assert [x.member for x in a["test"]] == [x.member for x in b["test"]]
    assert (len(a["train"]), len(a["val"]), len(a["test"])) == (70, 10, 20)
    # a random split mixes survey years across train and test (the leakage being measured)
    assert {x.group for x in a["test"]} & {x.group for x in a["train"]}
    members = [x.member for part in a.values() for x in part]
    assert sorted(members) == sorted(x.member for x in s)  # every image used exactly once
