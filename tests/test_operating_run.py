import numpy as np

from netsight.detect.operating_run import check, count_threshold


def test_count_threshold_flags_at_most_budget_per_image():
    scores = np.array([0.9, 0.8, 0.7, 0.7, 0.5, 0.1])
    t = count_threshold(scores, n_images=4, budget=0.5)  # at most 2 flagged
    assert np.count_nonzero(scores >= t) == 2
    t = count_threshold(scores, n_images=6, budget=0.5)  # 3 allowed, tie at 0.7 -> 2
    assert np.count_nonzero(scores >= t) == 2
    assert count_threshold(scores, n_images=1, budget=0.5) == float("inf")
    assert np.count_nonzero(scores >= count_threshold(scores, 100, 1.0)) == 6


def test_check_counts_missed_objects_in_recall():
    scores = np.array([0.9, 0.6, 0.3])
    real = np.array([1.0, 0.0, 1.0])
    r = check((scores, real, 4, 2), 0.5)  # 4 objects, only 2 ever detected
    assert r["tp"] == 1 and r["recall"] == 0.25 and r["fa_per_image"] == 0.5
