import io
import time

import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def client(runtime, mock_engine, stub_features):
    app = create_app(runtime)
    with TestClient(app) as c:
        yield c


def _wav_bytes(duration: float = 2.0, sr: int = 22050) -> bytes:
    import soundfile as sf

    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    sig = (0.3 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
    buf = io.BytesIO()
    sf.write(buf, sig, sr, format="WAV")
    return buf.getvalue()


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["cpu_only"] is True
    assert body["device"] == "cpu"


def test_spec(client):
    r = client.get("/api/spec")
    assert r.status_code == 200
    spec = r.json()
    assert spec["fps"] == 50.0
    assert spec["n_mels"] == 128
    assert spec["sample_rate"] == 22050


def test_models_listing(client):
    r = client.get("/api/models")
    assert r.status_code == 200
    names = [m["checkpoint"] for m in r.json()]
    assert "final0" in names
    assert "small0" in names


def test_analysis_happy_path(client):
    wav = _wav_bytes(3.0)
    r = client.post(
        "/api/analysis",
        files={"audio": ("song.wav", wav, "audio/wav")},
        data={"config": '{"checkpoint": "mock", "want_activations": true}'},
    )
    assert r.status_code == 200, r.text
    job = r.json()
    job_id = job["id"]
    assert job["state"] in ("queued", "running", "completed")

    # Poll until terminal.
    for _ in range(100):
        jr = client.get(f"/api/jobs/{job_id}").json()
        if jr["state"] in ("completed", "failed", "cancelled"):
            break
        time.sleep(0.05)
    assert jr["state"] == "completed", jr
    assert jr["result"]["counts"]["beats"] > 0
    assert jr["result"]["tempo"]["bpm"] is not None

    # Events available.
    ev = client.get(f"/api/jobs/{job_id}/events").json()
    assert any(e["stage"] == "inference" for e in ev)
    assert any(e["stage"] == "postprocess" for e in ev)

    # Artifact downloads.
    artifacts = jr["result"]["artifacts"]
    assert "json" in artifacts
    ar = client.get(f"/api/jobs/{job_id}/artifacts/json")
    assert ar.status_code == 200
    assert ar.json()["schema_version"] == "1.0"


def test_analysis_rejects_bad_config(client):
    wav = _wav_bytes(1.0)
    r = client.post(
        "/api/analysis",
        files={"audio": ("x.wav", wav, "audio/wav")},
        data={"config": "{not json}"},
    )
    assert r.status_code == 400


def test_missing_job_404(client):
    r = client.get("/api/jobs/does-not-exist")
    assert r.status_code == 404
