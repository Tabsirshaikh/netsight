import numpy as np

from netsight.datasets.ai4shipwrecks import mask_to_boxes, site_of, to_yolo_lines


def test_site_of():
    assert site_of("DM_Wilson_03") == "DM_Wilson"
    assert site_of("Montana_01.png") == "Montana"
    assert site_of("Lucinda_van_Valkenburg_12") == "Lucinda_van_Valkenburg"


def test_fragments_merge_and_specks_drop():
    m = np.zeros((200, 300), np.uint8)
    m[50:70, 50:90] = 1
    m[50:70, 95:120] = 1  # 5 px gap: same wreck
    m[150:160, 250:260] = 1  # 100 px speck (1 m): dropped
    boxes = mask_to_boxes(m)
    assert boxes.tolist() == [[50.0, 50.0, 120.0, 70.0]]


def test_empty_mask_and_yolo_line():
    assert mask_to_boxes(np.zeros((10, 10))).shape == (0, 4)
    line = to_yolo_lines(np.array([[0.0, 0.0, 50.0, 20.0]]), 100, 40)
    assert line == "0 0.250000 0.250000 0.500000 0.500000\n"
