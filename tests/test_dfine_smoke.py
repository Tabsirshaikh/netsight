"""Local smoke test of the D-FINE stack; skipped where torch/transformers are not installed."""

import io
import zipfile

import numpy as np
import pytest

torch = pytest.importorskip("torch")
pytest.importorskip("transformers")
Image = pytest.importorskip("PIL.Image")

from netsight.datasets.detection import read_yolo_zip  # noqa: E402
from netsight.detect.dfine import (  # noqa: E402
    TileDataset,
    collate,
    load_model,
    make_optimizer,
    predict_image,
)
from netsight.detect.training_tiles import build_train_tiles  # noqa: E402


@pytest.fixture(scope="module")
def model_and_processor():
    try:
        return load_model()
    except OSError as exc:  # no network and no cached checkpoint
        pytest.skip(f"D-FINE checkpoint unavailable: {exc}")


def _zip(tmp_path):
    rng = np.random.default_rng(0)
    path = tmp_path / "2020.zip"
    with zipfile.ZipFile(path, "w") as z:
        for i in range(2):
            img = rng.integers(40, 80, (480, 480)).astype(np.uint8)
            img[200:240, 100:160] = 230  # a bright target 60x40 px
            buf = io.BytesIO()
            Image.fromarray(img).save(buf, format="PNG")
            z.writestr(f"2020/{i}.png", buf.getvalue())
            z.writestr(f"2020/{i}.txt", "0 0.2708333 0.4583333 0.125 0.0833333\n")
    return path


def test_dataset_labels_are_normalised_cxcywh(tmp_path, model_and_processor):
    _, processor = model_and_processor
    samples = read_yolo_zip([_zip(tmp_path)], "synthetic", ["object"])
    tiles = build_train_tiles(samples, 480, neg_ratio=0.0, rng=np.random.default_rng(0))
    ds = TileDataset(samples, tiles, processor, augment=False)
    pixels, labels = ds[0]
    assert tuple(pixels.shape) == (3, 640, 640)
    assert labels["class_labels"].tolist() == [0]
    cx, cy, w, h = labels["boxes"][0].tolist()
    assert (cx, cy) == pytest.approx((130 / 480, 220 / 480), abs=2e-3)
    assert (w, h) == pytest.approx((60 / 480, 40 / 480), abs=2e-3)


def test_one_training_step_and_inference(tmp_path, model_and_processor):
    model, processor = model_and_processor
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model.to(device).train()
    samples = read_yolo_zip([_zip(tmp_path)], "synthetic", ["object"])
    tiles = build_train_tiles(samples, 320, neg_ratio=0.0, rng=np.random.default_rng(0))
    ds = TileDataset(samples, tiles, processor, augment=True)
    pixels, labels = collate([ds[i] for i in range(len(ds))])
    labels = [{k: v.to(device) for k, v in lab.items()} for lab in labels]
    opt = make_optimizer(model, 1e-4)
    out = model(pixel_values=pixels.to(device), labels=labels)
    assert torch.isfinite(out.loss)
    out.loss.backward()
    opt.step()
    image = np.asarray(Image.open(io.BytesIO(zipfile.ZipFile(samples[0].zip_path).read(
        samples[0].member))).convert("L"))
    boxes, scores = predict_image(model, processor, image, tile_px=320, device=device)
    assert boxes.ndim == 2 and boxes.shape[1] == 4 and len(boxes) == len(scores)
    if len(boxes):
        assert boxes[:, 2].max() <= 480.5 and boxes[:, 0].min() >= -0.5
