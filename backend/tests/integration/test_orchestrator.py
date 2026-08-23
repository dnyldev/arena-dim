import math

import pytest

from app.analysis.orchestrator import AnalysisOrchestrator
from app.core.config import AnalysisConfig
from app.core.errors import ModelWeightsMissingError
from app.domain.models import AudioInput
from app.events import JobReporter
from app.events.bus import EventBus


@pytest.mark.usefixtures("mock_engine", "stub_features")
def test_orchestrator_end_to_end(runtime, sine_wav):
    orch = AnalysisOrchestrator(runtime)
    reporter = JobReporter("job-int", EventBus())
    audio = AudioInput(
        path=sine_wav,
        original_filename="sine.wav",
        size_bytes=sine_wav.stat().st_size,
        content_type="audio/wav",
    )
    result = orch.run("job-int", audio, AnalysisConfig(checkpoint="mock"), reporter)

    # Mock engine produces beats every 0.5s.
    assert len(result.beats) > 0
    assert result.tempo.bpm is not None
    assert math.isclose(result.tempo.bpm, 120.0, rel_tol=0.05)
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
    # Validation OK.
    assert data["validation"]["ok"] is True
