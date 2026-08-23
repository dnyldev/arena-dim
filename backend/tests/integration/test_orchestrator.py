import math

import pytest

from app.analysis.orchestrator import AnalysisOrchestrator
from app.core.config import AnalysisConfig
from app.core.errors import ModelWeightsMissingError
from app.domain.models import AudioInput
from app.events import JobReporter
from app.events.bus import EventBus


@pytest.mark.usefixtures("mock_engine", "stub_features")
def test_orchestrator_end_to_end(runtime, sine_wav_long):
    orch = AnalysisOrchestrator(runtime)
    reporter = JobReporter("job-int", EventBus())
    audio = AudioInput(
        path=sine_wav_long,
        original_filename="sine_long.wav",
        size_bytes=sine_wav_long.stat().st_size,
        content_type="audio/wav",
    )
    result = orch.run("job-int", audio, AnalysisConfig(checkpoint="mock"), reporter)

    # Mock engine produces beats every 0.5s.
    assert len(result.beats) > 0
    assert result.tempo.bpm is not None
    assert math.isclose(result.tempo.bpm, 120.0, rel_tol=0.05)
    # Tempo curve is populated and stays close to 120 BPM throughout
    # (the mock engine produces a perfectly steady beat).
    assert len(result.tempo.curve) > 0
    for point in result.tempo.curve:
        assert math.isclose(point.bpm, 120.0, rel_tol=0.05)
    # Meter: mock engine places a downbeat every 4 beats -> 4/4.
    assert result.meter.beats_per_bar == 4
    assert result.meter.origin.value == "estimated"
    # Downbeats are a subset of beats.
    for d in result.downbeats:
        assert any(abs(d - b) < 1e-6 for b in result.beats)
    # Schema version present.
    assert result.schema_version == "1.0"
    # JSON is serialisable and has the expected fields.
    data = result.to_public_dict()
    assert data["schema_version"] == "1.0"
    assert data["config"]["device"] == "cpu"
    assert data["counts"]["beats"] == len(result.beats)
    assert "timing_ms" in data and "total" in data["timing_ms"]
    assert "meter" in data and data["meter"]["beats_per_bar"] == 4
    assert "curve" in data["tempo"] and len(data["tempo"]["curve"]) > 0
    # Validation OK.
    assert data["validation"]["ok"] is True
