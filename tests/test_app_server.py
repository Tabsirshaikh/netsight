"""CPU-only API contract tests. No models, prediction dump, or datasets."""

import hashlib
import io
import json
import math
from types import SimpleNamespace

import numpy as np
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from netsight.app.server import ModelBundle, Runtime, Sample, create_app


@pytest.fixture
def setup(tmp_path):
    calls = []
    contexts = []
    manifest = {
        "model_id": "fake-v0.4",
        "model_class": "research",
        "label": "Fake research model",
        "manifest_sha256": "a" * 64,
    }

    def predict(model, processor, image, **kwargs):
        calls.append((image.copy(), kwargs))
        return np.array([[2, 2, 15, 14], [18, 8, 30, 26]]), np.array([0.9, 0.4])

    def threshold(scores, n_images, budget):
        k = min(len(scores), math.floor(n_images * budget))
        return float(np.sort(scores)[-k]) if k else float("inf")

    def pack_writer(context, directory, ledger):
        contexts.append(context)
        public = {
            "survey_id": context["survey_id"],
            "contacts": context["contacts"],
            "inputs": context["inputs"],
        }
        (directory / "evidence_pack.json").write_text(json.dumps(public), encoding="utf-8")
        (directory / "evidence_pack.html").write_text(
            "<!doctype html><title>Evidence</title>", encoding="utf-8"
        )
        ledger.parent.mkdir(parents=True, exist_ok=True)
        with ledger.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps({"survey_id": context["survey_id"]}) + "\n")

    state = Runtime(
        device="cpu",
        models={
            key: ModelBundle(object(), object(), manifest) for key in ("general", "ghost-gear")
        },
        calibrator=SimpleNamespace(predict=lambda scores: scores * 0.8),
        calibration={"source": "fake validation"},
        dump=tmp_path / "nonexistent-dump",
        output_dir=tmp_path / "packs",
        ledger_path=tmp_path / "ledger.jsonl",
        predictor=predict,
        geometry=lambda *args: SimpleNamespace(
            level="indicative", reasons=["Synthetic geometry"], statement="Test claim."
        ),
        recall=lambda *args: (0.75, (0.6, 0.85)),
        threshold=threshold,
        evidence=lambda *args: SimpleNamespace(as_dict=lambda: {"shadow_present": False}),
        samples=[
            Sample(
                "sample-1",
                "held-out.png",
                "ghostvision",
                "test-group",
                np.zeros((32, 40), dtype=np.uint8),
            )
        ],
        pack_writer=pack_writer,
    )
    with TestClient(create_app(factory=lambda: state)) as client:
        yield client, calls, contexts


def image_bytes():
    buffer = io.BytesIO()
    Image.fromarray(np.full((32, 40), 100, dtype=np.uint8)).save(buffer, "PNG")
    return buffer.getvalue()


def analyze(client, budget="1", **fields):
    return client.post(
        "/api/analyze",
        data={"budget": budget, **fields},
        files=[("files", ("synthetic.png", image_bytes(), "image/png"))],
    )


def test_health_and_samples(setup):
    client, _, _ = setup
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["ok"] is True
    assert response.json()["device"] == "cpu"
    assert len(response.json()["models"]) == 2
    sample = client.get("/api/samples").json()["samples"][0]
    assert sample["group"] == "test-group"
    assert client.get(sample["url"]).headers["content-type"] == "image/png"


def test_analyze_synthetic_image(setup):
    client, calls, contexts = setup
    response = analyze(client, tta="false", profile="ghostvision")
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["model"]["id"] == "fake-v0.4"
    assert result["claim"]["level"] == "indicative"
    assert result["operating"]["flagged"] == 1
    assert result["operating"]["recall_ci"] == [0.6, 0.85]
    detections = result["images"][0]["detections"]
    assert len(detections) == 2
    assert detections[0]["flagged"] is True
    assert detections[1]["flagged"] is False
    assert detections[0]["probability"] == pytest.approx(0.72)
    assert detections[0]["evidence"]["shadow_present"] is False
    assert detections[1]["evidence"] == {}
    assert calls[0][0].dtype == np.uint8
    assert calls[0][1]["views"] == "none"
    assert contexts[0]["inputs"]["synthetic.png"] == hashlib.sha256(image_bytes()).hexdigest()
    assert len(contexts[0]["contacts"]) == 1
    assert (
        contexts[0]["operating"]["recall_source"]
        == "validation surveys, same budget rule (not this survey)"
    )
    assert client.get(result["images"][0]["url"]).status_code == 200


@pytest.mark.parametrize("budget,flagged", [("0.25", 0), ("1", 1), ("2", 2), ("3", 2)])
def test_budget_flagging(setup, budget, flagged):
    client, _, _ = setup
    response = analyze(client, budget=budget)
    assert response.status_code == 200
    assert response.json()["operating"]["flagged"] == flagged
    if flagged == 0:
        assert response.json()["operating"]["threshold"] is None


def test_bad_file_type(setup):
    client, calls, _ = setup
    response = client.post(
        "/api/analyze", files={"files": ("bad.exe", b"bad", "application/octet-stream")}
    )
    assert response.status_code == 415
    assert "file type" in response.json()["detail"]
    assert not calls


def test_pack_download(setup):
    client, _, _ = setup
    result = analyze(client).json()
    pack = client.get(result["packs"]["json"])
    assert pack.status_code == 200
    assert pack.json()["survey_id"] == result["survey_id"]
    assert "attachment" in pack.headers["content-disposition"]
    html = client.get(result["packs"]["html"])
    assert html.status_code == 200
    assert "<title>Evidence</title>" in html.text
    assert client.get("/api/packs/not-a-survey/evidence_pack.json").status_code == 404


def test_sample_input_and_validation(setup):
    client, _, _ = setup
    response = client.post("/api/analyze", data={"sample_ids": '["sample-1"]', "budget": "1"})
    assert response.status_code == 200
    assert response.json()["images"][0]["width"] == 40
    assert client.post("/api/analyze").status_code == 422
    assert analyze(client, budget="-1").status_code == 422
    assert analyze(client, profile="unknown").status_code == 422
    assert client.post("/api/analyze", data={"sample_ids": "missing"}).status_code == 404


def test_corrupt_image_and_too_many_images(setup):
    client, _, _ = setup
    assert (
        client.post(
            "/api/analyze", files={"files": ("bad.png", b"not an image", "image/png")}
        ).status_code
        == 400
    )
    response = client.post(
        "/api/analyze",
        files=[("files", (f"{n}.png", image_bytes(), "image/png")) for n in range(21)],
    )
    assert response.status_code == 422


def test_cors_is_local_only(setup):
    client, _, _ = setup
    allowed = client.get("/api/health", headers={"Origin": "http://127.0.0.1:5173"})
    assert allowed.headers["access-control-allow-origin"] == "http://127.0.0.1:5173"
    denied = client.get("/api/health", headers={"Origin": "http://example.com"})
    assert "access-control-allow-origin" not in denied.headers


def geotiff_bytes(pixel_m=0.5):
    import rasterio
    from rasterio.transform import from_origin

    buffer = io.BytesIO()
    with rasterio.MemoryFile() as memfile:
        with memfile.open(
            driver="GTiff", height=32, width=40, count=1, dtype="uint8",
            crs="EPSG:32643", transform=from_origin(500000, 2000000, pixel_m, pixel_m),
        ) as ds:
            ds.write(np.full((1, 32, 40), 100, np.uint8))
        buffer.write(memfile.read())
    return buffer.getvalue()


def analyze_tiff(client, budget, unit):
    return client.post(
        "/api/analyze",
        data={"budget": budget, "budget_unit": unit},
        files=[("files", ("survey.tif", geotiff_bytes(), "image/tiff"))],
    )


@pytest.mark.parametrize("budget,flagged", [("3000", 0), ("5000", 1), ("20000", 2)])
def test_budget_per_km2_on_georeferenced_survey(setup, budget, flagged):
    client, _, contexts = setup
    response = analyze_tiff(client, budget, "km2")
    assert response.status_code == 200, response.text
    operating = response.json()["operating"]
    # 32 x 40 seabed pixels of 0.5 m = 320 m2 = 0.00032 km2
    assert operating["unit"] == "km2"
    assert operating["area_km2"] == pytest.approx(0.00032)
    assert operating["flagged"] == flagged
    assert contexts[0]["operating"]["unit"] == "km2"
    assert "per km2" in contexts[0]["operating"]["recall_source"]
    from netsight.report import OperatingSummary

    OperatingSummary(**contexts[0]["operating"])  # the real pack writer accepts the context


def test_budget_per_km2_needs_metric_georeference(setup):
    client, _, _ = setup
    response = analyze(client, budget="5000", budget_unit="km2")
    assert response.status_code == 422
    assert "GeoTIFF" in response.json()["detail"]


def test_per_image_mode_reports_flagged_density_when_georeferenced(setup):
    client, _, _ = setup
    operating = analyze_tiff(client, "1", "image").json()["operating"]
    assert operating["unit"] == "image"
    assert operating["flagged_per_km2"] == pytest.approx(1 / 0.00032)
    assert analyze(client, budget="1").json()["operating"]["flagged_per_km2"] is None


def test_bad_budget_unit(setup):
    client, _, _ = setup
    assert analyze(client, budget="1", budget_unit="mile").status_code == 422
