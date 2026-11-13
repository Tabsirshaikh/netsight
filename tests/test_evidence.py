def test_shadow_found_on_either_side_and_side_reported():
    import numpy as np

    from netsight.evidence import evidence_both_sides

    img = np.full((80, 120), 120.0)
    img[30:40, 60:70] = 250.0  # object
    img[30:40, 40:60] = 10.0  # shadow to its LEFT (port side of a centre-nadir waterfall)
    box = (60, 30, 70, 40)
    ev = evidence_both_sides(img, box)
    assert ev["shadow_present"] is True and ev["shadow_side"] == "left"
    plain = np.full((80, 120), 120.0)
    plain[30:40, 60:70] = 250.0
    none = evidence_both_sides(plain, box)
    assert none["shadow_present"] is False and none["shadow_side"] is None
