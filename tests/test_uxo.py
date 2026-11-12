import pytest

from netsight.trust.uxo import assess_uxo, uxo_attributes, uxo_target_list
from netsight.trust.wording import check_wording


def test_attributes():
    a = uxo_attributes(0.4, 1.2)
    assert a.length_m == 1.2 and a.width_m == 0.4 and a.aspect == pytest.approx(3.0)
    assert a.cylinder_like is True
    assert uxo_attributes(float("nan"), 0.5).length_m is None
    assert uxo_attributes(None, None).cylinder_like is None
    with pytest.raises(ValueError):
        uxo_attributes(-1, 1)


@pytest.mark.parametrize(
    "attrs,kw,status",
    [
        (uxo_attributes(1.5, 0.5), {}, "pUXO_candidate"),
        (uxo_attributes(0.6, 0.5), {}, "below_pick_size"),
        (uxo_attributes(None, None), {}, "not_assessable"),
        (uxo_attributes(2.0, 1.0), {"contact_class": "rock_boulder"}, "rank_only"),
        (uxo_attributes(2.0, 1.0), {"seabed_class": "boulder_field"}, "rank_only"),
        (
            uxo_attributes(0.3, 0.2, mag_anomaly=True),
            {"contact_class": "rock_boulder"},
            "pUXO_candidate",
        ),
        (uxo_attributes(None, None, mag_anomaly=True), {}, "pUXO_candidate"),
    ],
)
def test_rules_and_priority(attrs, kw, status):
    a = assess_uxo(attrs, **kw)
    assert a.status == status
    assert a.rank_only == (status == "rank_only")
    assert check_wording(a.statement) == []


def test_pick_size_configurable():
    assert assess_uxo(uxo_attributes(0.6, 0.2), min_pick_size_m=0.5).status == "pUXO_candidate"


def test_target_list_order():
    rows = uxo_target_list(
        [
            {"contact_id": "a", "p_real": 0.2, "length_m": 0.3, "width_m": 0.2},
            {"contact_id": "b", "p_real": 0.4, "length_m": 1.4, "width_m": 0.4},
            {"contact_id": "c", "p_real": 0.9, "length_m": 1.1, "width_m": 0.5},
            {"contact_id": "d", "p_real": 0.5},
            {
                "contact_id": "e",
                "p_real": 0.8,
                "length_m": 3,
                "width_m": 2,
                "contact_class": "rock_boulder",
            },
        ]
    )
    assert [r["contact_id"] for r in rows] == ["c", "b", "d", "e", "a"]
