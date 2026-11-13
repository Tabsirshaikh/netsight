# ruff: noqa: B008  (FastAPI declares form/file fields as defaults)
"""NetSight's local research API.

Run with:
    uv run python -m netsight.app.server --port 8000

The module-level runtime_factory, or create_app(factory=...), is the injection
boundary. Importing this module does not load transformers, models, or datasets.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import io
import json
import logging
import math
import os
import re
import shutil
import time
import uuid
import warnings
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any

import anyio
import numpy as np
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from PIL import Image, ImageOps, UnidentifiedImageError

LOG = logging.getLogger(__name__)
MAX_BYTES = 50 * 1024 * 1024
MAX_IMAGES = 20
MAX_PIXELS = 40_000_000
EXTENSIONS = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"}
PROFILES = {"general", "ghostvision", "aquascan", "mine", "sctd", "subpipe"}
START_COMMAND = "uv run python -m netsight.app.server --port 8000"


@dataclass
class ModelBundle:
    model: Any
    processor: Any
    manifest: dict[str, Any]


@dataclass
class Sample:
    id: str
    name: str
    dataset: str
    group: str
    image: np.ndarray


@dataclass
class Runtime:
    """All data-dependent operations are replaceable in CPU-only tests."""

    device: str
    models: dict[str, ModelBundle]
    calibrator: Any
    calibration: dict[str, Any]
    dump: Path
    output_dir: Path
    ledger_path: Path
    predictor: Callable[..., Any]
    geometry: Callable[..., Any]
    recall: Callable[..., Any]
    threshold: Callable[..., Any]
    evidence: Callable[..., Any]
    samples: list[Sample] = field(default_factory=list)
    pack_writer: Callable[..., Any] | None = None
    # Real objects cut from validation surveys, per dataset, for completeness injection.
    targets: dict[str, list[Any]] = field(default_factory=dict)


# The detector proposes up to 100 candidates per image (raw score >= 0.01) for ranking and
# calibration. Unflagged candidates below this calibrated probability are not sent to the UI.
SAMPLE_DATASETS = (
    "ghostvision",
    "ghostvision_shift",
    "aquascan",
    "mine",
    "sctd",
    "subpipe",
    "ai4shipwrecks",
)
SAMPLES_PER_DATASET = 8  # 6 with labelled objects + 2 without, spread across surveys


def pick_samples(pool: list, n: int = SAMPLES_PER_DATASET, n_empty: int = 2) -> list:
    """Held-out samples spread evenly through the test set, mostly images with objects."""
    pos = [s for s in pool if len(s.boxes)]
    neg = [s for s in pool if not len(s.boxes)]

    def spread(items: list, k: int) -> list:
        if k <= 0 or not items:
            return []
        idx = np.unique(np.linspace(0, len(items) - 1, min(k, len(items))).round().astype(int))
        return [items[i] for i in idx]

    chosen = spread(pos, n - min(n_empty, len(neg)))
    return chosen + spread(neg, n - len(chosen))


MIN_SHOWN_PROBABILITY = 0.01


def json_safe(value: Any) -> Any:
    """JSON has no representation for an infinite, no-contact threshold."""
    if isinstance(value, Enum):
        return json_safe(value.value)
    if isinstance(value, np.ndarray):
        return json_safe(value.tolist())
    if isinstance(value, np.generic):
        return json_safe(value.item())
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [json_safe(v) for v in value]
    if isinstance(value, Path):
        return str(value)
    return value


def png_bytes(image: np.ndarray) -> bytes:
    buffer = io.BytesIO()
    Image.fromarray(image).save(buffer, format="PNG")
    return buffer.getvalue()


def onnx_predictor(onnx_path: Path, model: Any, fallback: Callable[..., Any]) -> Callable:
    """Predictor that runs ``model``'s ONNX export on the CPU (offline mode), with the same
    horizontal-flip TTA and box merge as the PyTorch path; other models use ``fallback``."""
    from netsight.detect.onnx_export import OnnxDetector, predict_image_onnx
    from netsight.detect.tta import weighted_box_fusion

    detector = OnnxDetector(onnx_path)

    def predict(m: Any, processor: Any, image: np.ndarray, **kw: Any):
        if m is not model:
            return fallback(m, processor, image, **kw)
        b, s = predict_image_onnx(detector, image, tile_px=kw.get("tile_px", 640))
        if kw.get("views", "hflip") == "none":
            return b, s
        w = image.shape[1]
        bf, sf = predict_image_onnx(
            detector, np.ascontiguousarray(image[:, ::-1]), tile_px=kw.get("tile_px", 640)
        )
        bf = np.asarray(bf, float).reshape(-1, 4).copy()
        bf[:, [0, 2]] = w - bf[:, [2, 0]]
        boxes, scores = weighted_box_fusion(
            [np.asarray(b, float).reshape(-1, 4), bf], [np.asarray(s, float), np.asarray(sf, float)]
        )
        return boxes[:100], np.clip(scores[:100], 0.0, 1.0)

    return predict


def default_runtime_factory() -> Runtime:
    import torch
    from transformers import AutoImageProcessor, DFineForObjectDetection

    from netsight.config import data_dir
    from netsight.demo.run_survey import (
        fit_calibrator,
        geometry_claim,
        validation_recall,
    )
    from netsight.detect.operating_run import count_threshold
    from netsight.detect.pilot import build_splits
    from netsight.detect.pixel_cache import PixelCache
    from netsight.detect.tta import predict_image_tta
    from netsight.evidence import evidence_features

    root = Path(data_dir())
    device = "cuda" if torch.cuda.is_available() else "cpu"
    models: dict[str, ModelBundle] = {}
    for key, relative in {
        "general": "runs/research_v0.4/model",
        "ghost-gear": "runs/ft_v0.4_ghostvision/model",
    }.items():
        directory = root / relative
        manifest = json.loads((directory / "manifest.json").read_text("utf-8"))
        required = {"model_id", "model_class", "label", "manifest_sha256"}
        if not required.issubset(manifest):
            raise ValueError(f"Incomplete manifest for {key}")
        model = DFineForObjectDetection.from_pretrained(str(directory))
        model.to(device)
        model.eval()
        models[key] = ModelBundle(
            model=model,
            processor=AutoImageProcessor.from_pretrained(str(directory)),
            manifest=manifest,
        )

    dump = root / "runs" / "calib_v0.4"
    calibrator, calibration = fit_calibrator(dump)
    all_splits = build_splits(root)
    splits = all_splits["test"]
    pixels = PixelCache(root / "cache" / "pixels")
    samples: list[Sample] = []
    for dataset in SAMPLE_DATASETS:
        for index, sample in enumerate(pick_samples(list(splits.get(dataset, [])))):
            identity = f"{dataset}:{sample.member}:{sample.group}:{index}"
            samples.append(
                Sample(
                    id=hashlib.sha256(identity.encode()).hexdigest()[:20],
                    name=Path(str(sample.member)).name,
                    dataset=str(sample.dataset_id),
                    group=str(sample.group),
                    image=np.asarray(pixels.get(sample), dtype=np.uint8),
                )
            )
    targets = build_target_library(all_splits["val"], pixels)
    predictor: Callable[..., Any] = predict_image_tta
    onnx = os.environ.get("NETSIGHT_ONNX")
    if onnx:
        predictor = onnx_predictor(Path(onnx), models["general"].model, predict_image_tta)
    return Runtime(
        targets=targets,
        device=device,
        models=models,
        calibrator=calibrator,
        calibration=calibration,
        dump=dump,
        output_dir=root / "runs" / "dashboard_packs",
        ledger_path=root / "runs" / "dashboard_ledger.jsonl",
        predictor=predictor,
        geometry=geometry_claim,
        recall=validation_recall,
        threshold=count_threshold,
        evidence=evidence_features,
        samples=samples,
    )


# Deliberately public: tests and local integrations may replace this before the
# first request. A runtime belongs to one app instance, never to a global cache.
runtime_factory: Callable[[], Runtime] = default_runtime_factory


class RequestSizeLimit:
    """Bound the *entire* multipart request, including chunked transfers.

    Read before invoking the multipart parser, so oversized bodies cannot spool
    unbounded temporary files. The maximum retained body is 50 MiB.
    """

    def __init__(self, app: Any) -> None:
        self.app = app

    async def __call__(self, scope: dict, receive: Callable, send: Callable) -> None:
        if scope["type"] != "http" or scope.get("method") != "POST":
            await self.app(scope, receive, send)
            return
        headers = dict(scope.get("headers", []))
        try:
            length = int(headers.get(b"content-length", b"0"))
        except ValueError:
            length = 0
        if length > MAX_BYTES:
            await JSONResponse({"detail": "Request exceeds the 50 MB limit."}, status_code=413)(
                scope, receive, send
            )
            return
        chunks: list[bytes] = []
        total = 0
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            chunk = message.get("body", b"")
            total += len(chunk)
            if total > MAX_BYTES:
                await JSONResponse({"detail": "Request exceeds the 50 MB limit."}, status_code=413)(
                    scope, receive, send
                )
                return
            chunks.append(chunk)
            if not message.get("more_body", False):
                break
        body = b"".join(chunks)
        delivered = False

        async def replay() -> dict:
            nonlocal delivered
            if not delivered:
                delivered = True
                return {"type": "http.request", "body": body, "more_body": False}
            return await receive()

        await self.app(scope, replay, send)


def decode_image(data: bytes, name: str) -> np.ndarray:
    if Path(name).suffix.lower() not in EXTENSIONS:
        raise HTTPException(415, f"{name}: unsupported file type. Use PNG, JPG, TIF, TIFF, or BMP.")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data)) as image:
                if image.format not in {"PNG", "JPEG", "TIFF", "BMP"}:
                    raise HTTPException(
                        415, f"{name}: image content does not match an allowed format."
                    )
                if image.width * image.height > MAX_PIXELS:
                    raise HTTPException(413, f"{name}: maximum image size is 40 million pixels.")
                # A multi-page TIFF contributes its first frame, as documented.
                image.seek(0)
                return np.array(ImageOps.exif_transpose(image).convert("L"), dtype=np.uint8)
    except HTTPException:
        raise
    except (
        UnidentifiedImageError,
        OSError,
        ValueError,
        Image.DecompressionBombWarning,
        Image.DecompressionBombError,
    ) as exc:
        raise HTTPException(400, f"{name}: cannot decode a safe image.") from exc


def write_evidence(context: dict[str, Any], out_dir: Path, ledger_path: Path) -> None:
    from netsight.report.evidence_pack import (
        Contact,
        OperatingSummary,
        build_pack,
        write_pack,
    )
    from netsight.trust.provenance import Ledger

    contacts = [Contact(**contact) for contact in context["contacts"]]
    operating = OperatingSummary(**context["operating"])
    pack = build_pack(
        survey_id=context["survey_id"],
        contacts=contacts,
        claim=context["claim"],
        manifest=context["manifest"],
        operating=operating,
        calibration=context["calibration"],
        created=context["created"],
        inputs=context["inputs"],
        completeness=context.get("completeness"),
        verification_plan=context.get("verification_plan"),
    )
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    write_pack(pack, out_dir, ledger=Ledger(ledger_path))


DOWNLOADS = {
    "evidence_pack.json": "application/json",
    "evidence_pack.html": "text/html",
    "contacts.geojson": "application/geo+json",
    "contacts.kml": "application/vnd.google-earth.kml+xml",
    "contacts.csv": "text/csv",
    "verification_plan.json": "application/json",
    "completeness.json": "application/json",
}
COMPLETENESS_GRID = (3, 3)
COMPLETENESS_PASSES = 3
COMPLETENESS_PER_PASS = 6
BANNER = (
    "RESEARCH OUTPUT - research model trained partly on research-only data; not for "
    "navigation, safety or legal decisions."
)


TARGETS_PER_DATASET = 40


def build_target_library(val_splits: dict, pixels: Any) -> dict[str, list[Any]]:
    """Up to 40 labelled objects per dataset, cut from validation surveys (never trained on;
    the dashboard's held-out samples come from test surveys, so no sample donates to itself)."""
    from netsight.trust.injection import template_from_box

    rng = np.random.default_rng(0)
    library: dict[str, list[Any]] = {}
    for dataset, samples in val_splits.items():
        boxes = [
            (s, b)
            for s in samples
            for b in np.asarray(s.boxes, float).reshape(-1, 4)
            if b[2] - b[0] >= 6 and b[3] - b[1] >= 6
        ]
        if not boxes:
            continue
        chosen = rng.choice(len(boxes), size=min(TARGETS_PER_DATASET, len(boxes)), replace=False)
        items = []
        for i in sorted(int(x) for x in chosen):
            sample, box = boxes[i]
            image = np.asarray(pixels.get(sample), np.uint8)
            try:
                items.append(template_from_box(image, box, source=f"val:{dataset}"))
            except ValueError:
                continue
        library[dataset] = items
    return library


def measure_completeness(
    runtime: Runtime,
    bundle: Any,
    images: list[tuple[str, np.ndarray, bytes]],
    predictions: list[tuple[np.ndarray, np.ndarray, np.ndarray]],
    threshold: float,
    tta: bool,
    profile: str = "general",
    claim_level: str = "calibrated",
) -> dict[str, Any]:
    """Inject reference targets into the survey's own images and measure Pd per image block."""
    from netsight.trust.bounds import one_sided_lower
    from netsight.trust.injection import completeness_map

    key = profile
    library = (
        [t for items in runtime.targets.values() for t in items]
        if key == "general"
        else list(runtime.targets.get(key, []))
    )
    if not library:
        return {"available": False, "reason": "no target library for this profile"}

    def predict(image: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        return runtime.predictor(
            bundle.model,
            bundle.processor,
            image,
            tile_px=640,
            device=runtime.device,
            views="hflip" if tta else "none",
        )

    cells = completeness_map(
        [image for _, image, _ in images],
        [(b, s) for b, s, _ in predictions],
        predict,
        threshold,
        library=library,
        rng=np.random.default_rng(0),
        passes=COMPLETENESS_PASSES,
        per_pass=COMPLETENESS_PER_PASS,
        grid=COMPLETENESS_GRID,
    )
    ok = [c for c in cells if c.status == "ok"]
    n = sum(c.n_trials for c in cells)
    k = sum(c.n_detected for c in cells)
    caveat = (
        "Pd applies to objects like those in the chosen profile's surveys, at their own "
        "pixel size; cells with fewer than 5 trials are marked insufficient, not "
        "estimated. On held-out surveys transplant Pd agreed with real recall on 4 of 6 "
        "datasets and was pessimistic on SubPipe and SCTD."
    )
    if claim_level != "calibrated":
        caveat = (
            f"INDICATIVE ONLY: this survey's geometry differs from the training data (claim "
            f"level {claim_level}), so the injected objects may not resemble this survey's "
            "objects and this Pd can be far too high. " + caveat
        )
    return {
        "available": True,
        "claim_level": claim_level,
        "method": (
            "real labelled objects from validation surveys (profile: "
            f"{profile}) transplanted onto the seabed of this survey, detected at this "
            "survey's operating threshold"
        ),
        "library_size": len(library),
        "profile": profile,
        "grid": list(COMPLETENESS_GRID),
        "trials": n,
        "detected": k,
        "pd": k / n if n else None,
        "pd_lower90": one_sided_lower(k, n, alpha=0.10) if n else None,
        "cells_ok": len(ok),
        "cells": [c.to_dict() for c in cells],
        "caveat": caveat,
    }


def write_survey_exports(
    out_dir: Path,
    survey_id: str,
    contacts: list[dict[str, Any]],
    claim_level: str,
    images: list[tuple[str, np.ndarray, bytes]],
    georefs: list[Any],
    completeness: dict[str, Any] | None,
) -> dict[str, str]:
    from netsight.app.geo_outputs import export_records, write_completeness_tiff, write_exports

    records = export_records(contacts, survey_id, claim_level)
    files = write_exports(out_dir, records, banner=BANNER, name=f"NetSight survey {survey_id}")
    if completeness is not None and completeness.get("available"):
        (out_dir / "completeness.json").write_text(json.dumps(json_safe(completeness)), "utf-8")
        files["completeness"] = "completeness.json"
        for i, ((_, image, _), georef) in enumerate(zip(images, georefs, strict=True)):
            if georef is None:
                continue
            cells = [c for c in completeness["cells"] if c["image_index"] == i]
            name = f"completeness_{i}.tif"
            write_completeness_tiff(
                out_dir / name, cells, georef, image.shape[:2], COMPLETENESS_GRID, banner=BANNER
            )
            files[f"completeness_tif_{i}"] = name
    return files


def analyze_sync(
    runtime: Runtime,
    images: list[tuple[str, np.ndarray, bytes]],
    model_key: str,
    profile: str,
    budget: float,
    tta: bool,
    show_all: bool = False,
    completeness: bool = False,
    budget_unit: str = "image",
) -> dict[str, Any]:
    from netsight.app.geo_outputs import contact_position, georeference
    from netsight.trust.area_budget import equivalent_image_budget, searched_area_km2

    started = time.perf_counter()
    georefs = [georeference(data, name) for name, _, data in images]
    metric = all(g is not None and g.projected for g in georefs)
    if budget_unit == "km2" and not metric:
        raise HTTPException(
            422,
            "A budget per km2 needs every image as a GeoTIFF in a projected (metre) CRS, so "
            "the searched seabed area is known. Use the per-image budget otherwise.",
        )
    area_km2 = (
        searched_area_km2([im for _, im, _ in images], [g.pixel_m for g in georefs])  # type: ignore[union-attr]
        if metric
        else None
    )
    bundle = runtime.models[model_key]
    predictions: list[tuple[np.ndarray, np.ndarray, np.ndarray]] = []
    for _, image, _ in images:
        boxes, scores = runtime.predictor(
            bundle.model,
            bundle.processor,
            image,
            tile_px=640,
            device=runtime.device,
            views="hflip" if tta else "none",
        )
        boxes = np.asarray(boxes, dtype=float).reshape(-1, 4)
        scores = np.asarray(scores, dtype=float).reshape(-1)
        if (
            len(boxes) != len(scores)
            or not np.isfinite(boxes).all()
            or not np.isfinite(scores).all()
        ):
            raise ValueError("Predictor returned invalid boxes or scores.")
        probabilities = (
            np.asarray(runtime.calibrator.predict(scores), dtype=float).reshape(-1)
            if len(scores)
            else np.empty(0)
        )
        if len(probabilities) != len(scores) or not np.isfinite(probabilities).all():
            raise ValueError("Calibrator returned invalid probabilities.")
        predictions.append((boxes, scores, np.clip(probabilities, 0, 1)))

    all_boxes = np.concatenate([p[0] for p in predictions], axis=0)
    all_scores = np.concatenate([p[1] for p in predictions], axis=0)
    if budget_unit == "km2":
        assert area_km2 is not None
        threshold = float(runtime.threshold(all_scores, area_km2, budget))
        image_budget = min(equivalent_image_budget(budget, area_km2, len(images)), 3.0)
        recall_source = (
            "validation surveys, same count rule at the equivalent per-image budget "
            f"({image_budget:.2f} per image; validation images have no pixel size, so this "
            "is an approximation of the per km2 rule)"
        )
    else:
        threshold = float(runtime.threshold(all_scores, len(images), budget))
        image_budget = budget
        recall_source = "validation surveys, same budget rule (not this survey)"
    envelope = None if profile == "general" else profile
    claim = runtime.geometry(runtime.dump, all_boxes, all_scores, envelope)
    recall, interval = runtime.recall(runtime.dump, image_budget, envelope)
    survey_id = uuid.uuid4().hex
    output: list[dict[str, Any]] = []
    contacts: list[dict[str, Any]] = []
    contact_number = 0
    hidden_candidates = 0
    for index, ((name, image, _), (boxes, scores, probabilities)) in enumerate(
        zip(images, predictions, strict=True)
    ):
        detections = []
        for box, score, probability in zip(boxes, scores, probabilities, strict=True):
            contact_number += 1
            contact_id = f"c{contact_number:05d}"
            flagged = bool(score >= threshold)
            if not show_all and not flagged and float(probability) < MIN_SHOWN_PROBABILITY:
                hidden_candidates += 1  # near-zero candidates: used for the threshold, not shown
                continue
            evidence = runtime.evidence(image, box).as_dict() if flagged else {}
            detection = {
                "id": contact_id,
                "box": box.tolist(),
                "raw_score": float(score),
                "probability": float(probability),
                "flagged": flagged,
                "evidence": evidence,
            }
            detections.append(detection)
            if flagged:
                contacts.append(
                    {
                        "contact_id": contact_id,
                        "image": name,
                        "box": tuple(float(x) for x in box),
                        "raw_score": float(score),
                        "probability": float(probability),
                        "evidence": evidence,
                        "position": (
                            contact_position(georefs[index], tuple(float(x) for x in box))
                            if georefs[index] is not None
                            else None
                        ),
                        "review": None,
                    }
                )
        output.append(
            {
                "index": index,
                "name": name,
                "width": int(image.shape[1]),
                "height": int(image.shape[0]),
                "detections": detections,
                "url": f"/api/packs/{survey_id}/images/{index}.png",
            }
        )

    context = {
        "survey_id": survey_id,
        "contacts": contacts,
        "claim": claim,
        "manifest": bundle.manifest,
        "operating": {
            "method": "label-free count threshold",
            "threshold": threshold,
            "budget_fa_per_unit": budget,
            "unit": budget_unit,
            "flagged": len(contacts),
            "area_km2": area_km2,
            "recall_estimate": recall,
            "recall_ci": tuple(interval),
            "recall_source": recall_source,
        },
        "calibration": runtime.calibration,
        "created": datetime.now(UTC).isoformat(),
        "inputs": {name: hashlib.sha256(data).hexdigest() for name, _, data in images},
    }
    completeness_result = (
        measure_completeness(
            runtime, bundle, images, predictions, threshold, tta, profile, claim.level
        )
        if completeness
        else None
    )
    if completeness_result is not None and completeness_result.get("available"):
        context["completeness"] = json_safe(completeness_result)
    from netsight.app.geo_outputs import export_records
    from netsight.export.plan import verification_plan

    context["verification_plan"] = json_safe(
        verification_plan(export_records(contacts, survey_id, claim.level))
    )
    out_dir = runtime.output_dir / survey_id
    out_dir.mkdir(parents=True, exist_ok=False)
    try:
        (runtime.pack_writer or write_evidence)(context, out_dir, runtime.ledger_path)
        exports = write_survey_exports(
            out_dir, survey_id, contacts, claim.level, images, georefs, completeness_result
        )
        previews = out_dir / "images"
        previews.mkdir(exist_ok=True)
        for index, (_, image, _) in enumerate(images):
            (previews / f"{index}.png").write_bytes(png_bytes(image))
    except Exception:
        shutil.rmtree(out_dir, ignore_errors=True)
        raise

    return json_safe(
        {
            "survey_id": survey_id,
            "model": {
                "id": bundle.manifest["model_id"],
                "label": bundle.manifest["label"],
                "model_class": bundle.manifest["model_class"],
            },
            "claim": {
                "level": claim.level,
                "statement": claim.statement,
                "reasons": claim.reasons,
            },
            "operating": {
                "threshold": threshold,
                "budget": budget,
                "unit": budget_unit,
                "area_km2": area_km2,
                "flagged_per_km2": len(contacts) / area_km2 if area_km2 else None,
                "flagged": len(contacts),
                "recall": recall,
                "recall_ci": interval,
                "recall_source": context["operating"]["recall_source"],
            },
            "images": output,
            "timing_ms": round((time.perf_counter() - started) * 1000, 1),
            "hidden_candidates": hidden_candidates,
            "packs": {
                "json": f"/api/packs/{survey_id}/evidence_pack.json",
                "html": f"/api/packs/{survey_id}/evidence_pack.html",
                **{k: f"/api/packs/{survey_id}/{v}" for k, v in exports.items()},
            },
            "georeferenced": [g is not None for g in georefs],
            "positions": {
                c["contact_id"]: c["position"] for c in contacts if c["position"] is not None
            },
            "completeness": completeness_result,
            "profile": profile,
            "tta": tta,
        }
    )


def create_app(factory: Callable[[], Runtime] | None = None) -> FastAPI:
    app = FastAPI(title="NetSight research dashboard", version="1")
    app.add_middleware(RequestSizeLimit)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://127.0.0.1:5173", "http://127.0.0.1:4173"],
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )
    lock = asyncio.Lock()
    runtime: Runtime | None = None

    async def get_runtime() -> Runtime:
        nonlocal runtime
        if runtime is None:
            async with lock:
                if runtime is None:
                    try:
                        with anyio.CancelScope(shield=True):
                            runtime = await anyio.to_thread.run_sync(factory or runtime_factory)
                    except Exception as exc:
                        LOG.exception("Dashboard initialization failed")
                        raise HTTPException(
                            503,
                            "Research assets could not be initialized. Check model manifests, "
                            "held-out datasets and runs/calib_v0.4. "
                            f"Start command: {START_COMMAND}",
                        ) from exc
        return runtime

    @app.exception_handler(RequestValidationError)
    async def invalid_request(_request: Any, exc: RequestValidationError) -> JSONResponse:
        details = "; ".join(
            f"{'.'.join(str(p) for p in error['loc'])}: {error['msg']}" for error in exc.errors()
        )
        return JSONResponse({"detail": details}, status_code=422)

    @app.get("/api/health")
    async def health() -> dict:
        state = await get_runtime()
        return {
            "ok": True,
            "device": state.device,
            "models": [
                {"key": key, **json_safe(bundle.manifest)} for key, bundle in state.models.items()
            ],
        }

    @app.get("/api/samples")
    async def samples() -> dict:
        state = await get_runtime()
        return {
            "samples": [
                {
                    "id": sample.id,
                    "name": sample.name,
                    "dataset": sample.dataset,
                    "group": sample.group,
                    "width": int(sample.image.shape[1]),
                    "height": int(sample.image.shape[0]),
                    "url": f"/api/samples/{sample.id}.png",
                }
                for sample in state.samples
            ]
        }

    @app.get("/api/samples/{sample_id}.png")
    async def sample_png(sample_id: str) -> Response:
        state = await get_runtime()
        sample = next((s for s in state.samples if s.id == sample_id), None)
        if sample is None:
            raise HTTPException(404, "Unknown held-out sample.")
        content = await anyio.to_thread.run_sync(png_bytes, sample.image)
        return Response(
            content, media_type="image/png", headers={"Cache-Control": "private, max-age=3600"}
        )

    @app.post("/api/analyze")
    async def analyze(
        files: list[UploadFile] | None = File(default=None),
        sample_ids: list[str] | None = Form(default=None),
        model: str = Form(default="general"),
        profile: str = Form(default="general"),
        budget: float = Form(default=1.0),
        tta: bool = Form(default=True),
        show_all: bool = Form(default=False),
        completeness: bool = Form(default=False),
        budget_unit: str = Form(default="image"),
    ) -> dict:
        if model not in {"general", "ghost-gear"}:
            raise HTTPException(422, "model must be general or ghost-gear.")
        if profile not in PROFILES:
            raise HTTPException(422, "Unknown applicability profile.")
        if budget_unit not in {"image", "km2"}:
            raise HTTPException(422, "budget_unit must be image or km2.")
        limit = 3 if budget_unit == "image" else 100_000
        if not math.isfinite(budget) or budget < 0 or budget > limit:
            raise HTTPException(
                422, f"budget must be a finite number between 0 and {limit} per {budget_unit}."
            )
        ids: list[str] = []
        for value in sample_ids or []:
            if value.startswith("["):
                try:
                    decoded = json.loads(value)
                    if not isinstance(decoded, list) or not all(
                        isinstance(x, str) for x in decoded
                    ):
                        raise ValueError()
                    ids.extend(decoded)
                except (ValueError, TypeError) as exc:
                    raise HTTPException(422, "sample_ids must contain sample identifiers.") from exc
            else:
                ids.extend(x.strip() for x in value.split(",") if x.strip())
        uploads = files or []
        if not 1 <= len(uploads) + len(ids) <= MAX_IMAGES:
            raise HTTPException(422, "Supply between 1 and 20 images as files or sample_ids.")
        # Reject extensions before initializing expensive research assets.
        for upload in uploads:
            if Path(upload.filename or "").suffix.lower() not in EXTENSIONS:
                raise HTTPException(415, "Unsupported file type. Use PNG, JPG, TIF, TIFF, or BMP.")
        state = await get_runtime()
        images: list[tuple[str, np.ndarray, bytes]] = []
        total = 0
        names: set[str] = set()

        def unique_name(name: str) -> str:
            name = Path(name.replace("\\", "/")).name or "image.png"
            original = name
            suffix = 2
            while name in names:
                name = f"{Path(original).stem}-{suffix}{Path(original).suffix}"
                suffix += 1
            names.add(name)
            return name

        for upload in uploads:
            try:
                data = await upload.read(MAX_BYTES + 1)
            finally:
                await upload.close()
            total += len(data)
            if total > MAX_BYTES:
                raise HTTPException(413, "Images exceed the 50 MB request limit.")
            name = unique_name(upload.filename or "image.png")
            image = await anyio.to_thread.run_sync(decode_image, data, name)
            images.append((name, image, data))
        by_id = {s.id: s for s in state.samples}
        for sample_id in ids:
            if sample_id not in by_id:
                raise HTTPException(404, f"Unknown sample: {sample_id}")
            sample = by_id[sample_id]
            data = await anyio.to_thread.run_sync(png_bytes, sample.image)
            total += len(data)
            if total > MAX_BYTES:
                raise HTTPException(413, "Resolved sample images exceed 50 MB.")
            images.append((unique_name(Path(sample.name).stem + ".png"), sample.image, data))

        # The lock covers prediction, calibration, pack emission, and ledger writes.
        # Shielding ensures a disconnect cannot release it while a worker still runs.
        async with lock:
            try:
                with anyio.CancelScope(shield=True):
                    return await anyio.to_thread.run_sync(
                        analyze_sync,
                        state,
                        images,
                        model,
                        profile,
                        budget,
                        tta,
                        show_all,
                        completeness,
                        budget_unit,
                    )
            except HTTPException:
                raise
            except Exception as exc:
                LOG.exception("Survey analysis failed")
                raise HTTPException(
                    500,
                    "Analysis failed. Check the API terminal for details; "
                    "no completed pack was returned.",
                ) from exc

    def pack_directory(state: Runtime, survey_id: str) -> Path:
        if not re.fullmatch(r"[a-f0-9]{32}", survey_id):
            raise HTTPException(404, "Unknown survey.")
        return state.output_dir / survey_id

    @app.get("/api/packs/{survey_id}/images/{index}.png")
    async def preview(survey_id: str, index: int) -> FileResponse:
        state = await get_runtime()
        if not 0 <= index < MAX_IMAGES:
            raise HTTPException(404, "Unknown image.")
        path = pack_directory(state, survey_id) / "images" / f"{index}.png"
        if not path.is_file():
            raise HTTPException(404, "Unknown image.")
        return FileResponse(path, media_type="image/png")

    @app.get("/api/packs/{survey_id}/{filename}")
    async def download(survey_id: str, filename: str) -> FileResponse:
        if filename not in DOWNLOADS and not re.fullmatch(r"completeness_\d{1,2}\.tif", filename):
            raise HTTPException(404, "Unknown pack file.")
        state = await get_runtime()
        path = pack_directory(state, survey_id) / filename
        if not path.is_file():
            raise HTTPException(404, "Evidence pack not found.")
        return FileResponse(
            path,
            media_type=DOWNLOADS.get(filename, "image/tiff"),
            filename=None if filename.endswith(".html") else filename,
        )

    return app


app = create_app()


def main() -> None:
    import uvicorn

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument(
        "--onnx",
        type=Path,
        default=None,
        help="offline CPU mode: run the general model from this ONNX export",
    )
    args = parser.parse_args()
    if args.onnx is not None:
        os.environ["NETSIGHT_ONNX"] = str(args.onnx)
    uvicorn.run(app, host="127.0.0.1", port=args.port)


if __name__ == "__main__":
    main()
