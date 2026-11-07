import io
import pickle
import zipfile

import numpy as np
import pytest

Image = pytest.importorskip("PIL.Image")

from netsight.datasets.detection import read_yolo_zip  # noqa: E402
from netsight.detect.pixel_cache import PixelCache, build_pixel_cache  # noqa: E402


def _zip(tmp_path, n=3):
    rng = np.random.default_rng(0)
    z = tmp_path / "2020.zip"
    arrays = {}
    with zipfile.ZipFile(z, "w") as f:
        for i in range(n):
            a = rng.integers(0, 255, (40, 60)).astype(np.uint8)
            buf = io.BytesIO()
            Image.fromarray(a).save(buf, format="PNG")  # lossless: cache must match exactly
            f.writestr(f"2020/{i}.png", buf.getvalue())
            f.writestr(f"2020/{i}.txt", "")
            arrays[f"2020/{i}.png"] = a
    return z, arrays


def test_build_then_read_gives_identical_pixels(tmp_path):
    z, arrays = _zip(tmp_path)
    samples = read_yolo_zip([z], "d", ["o"])
    stats = build_pixel_cache(samples, tmp_path / "cache")
    assert stats == {"written": 3, "skipped": 0}
    cache = PixelCache(tmp_path / "cache")
    for s in samples:
        np.testing.assert_array_equal(np.asarray(cache.get(s)), arrays[s.member])


def test_second_build_skips_existing(tmp_path):
    z, _ = _zip(tmp_path)
    samples = read_yolo_zip([z], "d", ["o"])
    build_pixel_cache(samples, tmp_path / "cache")
    assert build_pixel_cache(samples, tmp_path / "cache") == {"written": 0, "skipped": 3}


def test_uncached_sample_falls_back_to_zip(tmp_path):
    z, arrays = _zip(tmp_path)
    samples = read_yolo_zip([z], "d", ["o"])
    build_pixel_cache(samples[:1], tmp_path / "cache")
    cache = PixelCache(tmp_path / "cache")
    np.testing.assert_array_equal(np.asarray(cache.get(samples[2])), arrays[samples[2].member])


def test_changed_zip_invalidates_entries(tmp_path):
    z, _ = _zip(tmp_path)
    samples = read_yolo_zip([z], "d", ["o"])
    build_pixel_cache(samples, tmp_path / "cache")
    z.write_bytes(z.read_bytes() + b"")  # same bytes, new mtime: still the same file
    import os
    import time

    os.utime(z, (time.time() + 10, time.time() + 10))
    assert build_pixel_cache(samples, tmp_path / "cache")["written"] == 3


def test_cache_is_picklable_for_worker_processes(tmp_path):
    z, arrays = _zip(tmp_path)
    samples = read_yolo_zip([z], "d", ["o"])
    build_pixel_cache(samples, tmp_path / "cache")
    clone = pickle.loads(pickle.dumps(PixelCache(tmp_path / "cache")))
    np.testing.assert_array_equal(np.asarray(clone.get(samples[0])), arrays[samples[0].member])
