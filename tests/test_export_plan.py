"""Hand-computed ranking totals and connected re-survey regions."""

import math

import numpy as np
import pytest

from netsight.export.plan import resurvey_regions, verification_plan


def test_verification_plan():
    def record(identifier, probability, **changes):
        return {
            "contact_id": identifier,
            "lon": 12,
            "lat": 34,
            "p_real": probability,
            "ellipse95": None,
            "claim_level": "calibrated",
        } | changes

    contacts = [
        record("b", 0.5),
        record("a", 0.5),
        record("c", 0.25),
        record("d", 1, claim_level="withdrawn"),
        record("e", 0.25, lon=None),
    ]
    plan = verification_plan(contacts)
    entries = plan["entries"]
    assert [entry["contact_id"] for entry in entries] == ["a", "b", "c"]
    assert [entry["rank"] for entry in entries] == [1, 2, 3]
    assert [entry["cumulative_expected_real"] for entry in entries] == [0.5, 1, 1.25]
    assert plan["expected_real_total"] == 1.5
    assert plan["excluded_withdrawn"] == 1
    assert plan["excluded_no_position"] == 1
    assert entries[0]["lon"] == 12
    assert entries[0]["lat"] == 34
    assert entries[0]["ellipse95"] is None
    limited = verification_plan(contacts, top_n=1)
    assert len(limited["entries"]) == 1
    assert limited["expected_real_total"] == 1.5
    assert verification_plan(contacts, top_n=0)["entries"] == []
    with pytest.raises(ValueError, match="top_n"):
        verification_plan(contacts, top_n=-1)


def test_three_resurvey_regions():
    grid = np.array(
        [
            [0.1, 0.2, 1, 1, 0.3],
            [1, 1, 1, 1, 1],
            [1, 1, 1, 1, 1],
            [np.nan, np.nan, 1, 1, 1],
        ]
    )
    regions = resurvey_regions(
        grid, origin_ul_x=100, origin_ul_y=200, cell_size_m=10, threshold=0.5
    )
    assert len(regions) == 3
    assert [region["cells"] for region in regions] == [2, 2, 1]
    assert [region["area_m2"] for region in regions] == [200, 200, 100]
    assert [region["reason"] for region in regions] == [
        "pd_below_threshold",
        "not_searched",
        "pd_below_threshold",
    ]
    assert regions[0]["ring"] == [(100, 200), (100, 190), (120, 190), (120, 200), (100, 200)]
    assert regions[1]["ring"] == [(100, 170), (100, 160), (120, 160), (120, 170), (100, 170)]
    assert regions[2]["ring"] == [(140, 200), (140, 190), (150, 190), (150, 200), (140, 200)]
    assert regions[0]["min_pd"] == 0.1
    assert math.isnan(regions[1]["min_pd"])
    assert regions[2]["min_pd"] == 0.3


def test_diagonal_connectivity_and_majority_tie():
    regions = resurvey_regions(
        np.array([[np.nan, 0.5], [1, 0.25]]),
        origin_ul_x=0,
        origin_ul_y=2,
        cell_size_m=1,
        threshold=0.5,
    )
    assert len(regions) == 1
    assert regions[0]["cells"] == 2
    assert regions[0]["area_m2"] == 2
    assert regions[0]["reason"] == "pd_below_threshold"
    assert regions[0]["min_pd"] == 0.25
    assert regions[0]["ring"] == [(0, 2), (0, 0), (2, 0), (2, 2), (0, 2)]
    assert (
        resurvey_regions(
            np.ones((1, 1)), origin_ul_x=0, origin_ul_y=1, cell_size_m=1, threshold=0.5
        )
        == []
    )
