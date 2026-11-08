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
    splits = build_splits(root)["test"]
    pixels = PixelCache(root / "cache" / "pixels")
    samples: list[Sample] = []
    for dataset in ("ghostvision", "ghostvision_shift", "aquascan", "mine", "sctd", "subpipe"):
        for index, sample in enumerate(list(splits.get(dataset, []))[:2]):
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
    return Runtime(
        device=device,
        models=models,
        calibrator=calibrator,
        calibration=calibration,
        dump=dump,
        output_dir=root / "runs" / "dashboard_packs",
        ledger_path=root / "runs" / "dashboard_ledger.jsonl",
        predictor=predict_image_tta,
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
    )
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    write_pack(pack, out_dir, ledger=Ledger(ledger_path))


def analyze_sync(
    runtime: Runtime,
    images: list[tuple[str, np.ndarray, bytes]],
    model_key: str,
    profile: str,
    budget: float,
    tta: bool,
) -> dict[str, Any]:
    started = time.perf_counter()
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
    threshold = float(runtime.threshold(all_scores, len(images), budget))
    envelope = None if profile == "general" else profile
    claim = runtime.geometry(runtime.dump, all_boxes, all_scores, envelope)
    recall, interval = runtime.recall(runtime.dump, budget, envelope)
    survey_id = uuid.uuid4().hex
    output: list[dict[str, Any]] = []
    contacts: list[dict[str, Any]] = []
    contact_number = 0
    for index, ((name, image, _), (boxes, scores, probabilities)) in enumerate(
        zip(images, predictions, strict=True)
    ):
        detections = []
        for box, score, probability in zip(boxes, scores, probabilities, strict=True):
            contact_number += 1
            contact_id = f"c{contact_number:05d}"
            flagged = bool(score >= threshold)
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
                        "position": None,
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
            "unit": "image",
            "flagged": len(contacts),
            "recall_estimate": recall,
            "recall_ci": tuple(interval),
            "recall_source": "validation surveys, same budget rule (not this survey)",
        },
        "calibration": runtime.calibration,
        "created": datetime.now(UTC).isoformat(),
        "inputs": {name: hashlib.sha256(data).hexdigest() for name, _, data in images},
    }
    out_dir = runtime.output_dir / survey_id
    out_dir.mkdir(parents=True, exist_ok=False)
    try:
        (runtime.pack_writer or write_evidence)(context, out_dir, runtime.ledger_path)
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
                "flagged": len(contacts),
                "recall": recall,
                "recall_ci": interval,
                "recall_source": context["operating"]["recall_source"],
            },
            "images": output,
            "timing_ms": round((time.perf_counter() - started) * 1000, 1),
            "packs": {
                "json": f"/api/packs/{survey_id}/evidence_pack.json",
                "html": f"/api/packs/{survey_id}/evidence_pack.html",
            },
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
    ) -> dict:
        if model not in {"general", "ghost-gear"}:
            raise HTTPException(422, "model must be general or ghost-gear.")
        if profile not in PROFILES:
            raise HTTPException(422, "Unknown applicability profile.")
        if not math.isfinite(budget) or budget < 0 or budget > 3:
            raise HTTPException(422, "budget must be a finite number between 0 and 3.")
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
                        analyze_sync, state, images, model, profile, budget, tta
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
        if filename not in {"evidence_pack.json", "evidence_pack.html"}:
            raise HTTPException(404, "Unknown pack file.")
        state = await get_runtime()
        path = pack_directory(state, survey_id) / filename
        if not path.is_file():
            raise HTTPException(404, "Evidence pack not found.")
        return FileResponse(
            path,
            media_type="application/json" if filename.endswith(".json") else "text/html",
            filename=filename if filename.endswith(".json") else None,
        )

    return app


app = create_app()


def main() -> None:
    import uvicorn

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    uvicorn.run(app, host="127.0.0.1", port=args.port)


if __name__ == "__main__":
    main()
