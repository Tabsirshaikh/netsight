"""Raw-pixel image cache on local disk: decode each image once, read tiles without decoding.

Training cuts many tiles from large images (1920x1080 screenshots, 5000x500 waterfalls) in a
shuffled order, so an in-memory cache misses and every tile re-decodes its whole image. Here
each image is decoded once to an uncompressed .npy file and memory-mapped, so a tile costs only
the bytes it reads. Pixels are identical to decoding the source (lossless formats; JPEG decoding
is deterministic), so training results do not change, only speed.

    python -m netsight.detect.pixel_cache            # build for all research datasets
"""

from __future__ import annotations

import hashlib
import io
import json
import sys
import zipfile
from collections.abc import Sequence
from pathlib import Path

import numpy as np

from netsight.datasets.detection import DetectionSample

INDEX = "index.json"


def _key(sample: DetectionSample) -> str:
    return hashlib.sha1(f"{sample.zip_path}|{sample.member}".encode()).hexdigest()[:24]


def _zip_key(path: str) -> str:
    st = Path(path).stat()
    return f"{st.st_size}:{int(st.st_mtime)}"


def _decode(z: zipfile.ZipFile, member: str) -> np.ndarray:
    from PIL import Image

    return np.asarray(Image.open(io.BytesIO(z.read(member))).convert("L"), dtype=np.uint8)


def build_pixel_cache(
    samples: Sequence[DetectionSample], cache_dir: str | Path, *, flush_every: int = 500
) -> dict[str, int]:
    """Decode every sample once into cache_dir; skip entries that are still valid."""
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    index_path = cache_dir / INDEX
    index = json.loads(index_path.read_text(encoding="utf-8")) if index_path.exists() else {}
    zip_keys: dict[str, str] = {}
    zips: dict[str, zipfile.ZipFile] = {}
    written = skipped = 0
    try:
        for s in samples:
            k = _key(s)
            zk = zip_keys.setdefault(s.zip_path, _zip_key(s.zip_path))
            entry = index.get(k)
            if entry and entry["zip_key"] == zk and (cache_dir / f"{k}.npy").exists():
                skipped += 1
                continue
            z = zips.get(s.zip_path) or zips.setdefault(s.zip_path, zipfile.ZipFile(s.zip_path))
            img = _decode(z, s.member)
            np.save(cache_dir / f"{k}.npy", img, allow_pickle=False)
            index[k] = {"zip_key": zk, "shape": list(img.shape)}
            written += 1
            if written % flush_every == 0:
                index_path.write_text(json.dumps(index), encoding="utf-8")
    finally:
        for z in zips.values():
            z.close()
        index_path.write_text(json.dumps(index), encoding="utf-8")
    return {"written": written, "skipped": skipped}


class PixelCache:
    """Drop-in for ImageCache: memory-mapped cached pixels, decoding from the zip if missing."""

    def __init__(self, cache_dir: str | Path) -> None:
        self.cache_dir = Path(cache_dir)
        path = self.cache_dir / INDEX
        self._index = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
        self._zip_keys: dict[str, str] = {}
        self._zips: dict[str, zipfile.ZipFile] = {}

    def __getstate__(self):  # DataLoader workers reopen everything themselves
        return {"cache_dir": str(self.cache_dir)}

    def __setstate__(self, state):
        self.__init__(state["cache_dir"])

    def get(self, sample: DetectionSample) -> np.ndarray:
        k = _key(sample)
        entry = self._index.get(k)
        zk = self._zip_keys.setdefault(sample.zip_path, _zip_key(sample.zip_path))
        path = self.cache_dir / f"{k}.npy"
        if entry and entry["zip_key"] == zk and path.exists():
            return np.load(path, mmap_mode="r")
        z = self._zips.get(sample.zip_path)
        if z is None:
            z = self._zips[sample.zip_path] = zipfile.ZipFile(sample.zip_path)
        return _decode(z, sample.member)


def _lower_priority() -> None:
    """Run below normal priority so building never competes with a training run."""
    if sys.platform == "win32":
        import ctypes

        below_normal = 0x00004000
        ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(),
                                                below_normal)
    else:
        import os

        os.nice(10)


def main() -> int:
    from netsight.config import data_dir
    from netsight.detect.pilot import build_splits

    _lower_priority()
    splits = build_splits(data_dir())
    samples = splits["train"] + [s for part in ("val", "test")
                                 for v in splits[part].values() for s in v]
    stats = build_pixel_cache(samples, data_dir() / "cache" / "pixels")
    print(json.dumps({"images": len(samples), **stats}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
