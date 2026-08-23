"""Analysis orchestrator.

Runs the full pipeline for a single :class:`AudioInput`:

    validate → probe → load → normalize → resample →
    feature extraction → model load → inference →
    postprocess → validation → tempo → rhythm →
    result construction → artifacts

Each stage emits events through the job reporter, records timing, and
raises a typed :class:`BeatAnalysisError` on failure.  The orchestrator
is independent of FastAPI; the API layer calls it from a worker.
"""

from __future__ import annotations

import time
from typing import Any

import numpy as np

from app.analysis.numbering import infer_beat_numbers
from app.analysis.rhythm import RhythmAnalyzer
from app.analysis.tempo import TempoAnalyzer
from app.analysis.validator import BeatValidator
from app.artifacts import ArtifactGenerator
from app.audio import AudioService
from app.core.config import AnalysisConfig, BeatThisSpec, RuntimeConfig
from app.core.errors import (
    BeatAnalysisError,
    ModelWeightsMissingError,
    wrap_exception,
)
from app.domain.models import (
    AudioInput,
    AudioProbe,
    BeatAnalysisResult,
)
from app.engines.factory import create_engine
from app.events import EventStage, JobReporter
from app.features import LogMelSpectrogram
from app.postprocess import build_postprocessor


class AnalysisOrchestrator:
    def __init__(
        self,
        runtime: RuntimeConfig,
        audio_service: AudioService | None = None,
        feature_extractor: LogMelSpectrogram | None = None,
        artifact_generator: ArtifactGenerator | None = None,
    ) -> None:
        self.runtime = runtime
        self.audio = audio_service or AudioService(runtime)
        # Defer construction: LogMelSpectrogram imports torch, which is
        # only needed at analysis time. The app must start (and serve
        # /api/health) even when torch/beat-this are not installed.
        self._features = feature_extractor
        self.artifacts = artifact_generator or ArtifactGenerator(runtime)
        self.validator = BeatValidator()
        self.tempo = TempoAnalyzer()
        self.rhythm = RhythmAnalyzer()

    @property
    def features(self) -> LogMelSpectrogram:
        if self._features is None:
            self._features = LogMelSpectrogram(self.runtime.device)
        return self._features

    def run(
        self,
        job_id: str,
        audio_input: AudioInput,
        config: AnalysisConfig,
        reporter: JobReporter,
    ) -> BeatAnalysisResult:
        timing: dict[str, float] = {}
        t_total = time.perf_counter()

        # ----- validate ------------------------------------------------- #
        config.validate()

        # ----- probe ---------------------------------------------------- #
        t0 = time.perf_counter()
        reporter.started(EventStage.PROBE, "Probing audio metadata")
        probe = self.audio.probe(audio_input)
        timing["probe"] = time.perf_counter() - t0
        reporter.completed(
            EventStage.PROBE,
            f"{probe.duration_sec:.2f}s | {probe.sample_rate} Hz | "
            f"{probe.channels} ch",
            duration_sec=probe.duration_sec,
            sample_rate=probe.sample_rate,
            channels=probe.channels,
        )

        # ----- load + normalize + resample ------------------------------ #
        t0 = time.perf_counter()
        audio_data = self.audio.load_prepared(audio_input, probe, reporter)
        timing["audio_prepare"] = time.perf_counter() - t0

        # ----- feature extraction --------------------------------------- #
        t0 = time.perf_counter()
        spect = self.features.extract(audio_data, reporter)
        timing["spectrogram"] = time.perf_counter() - t0

        # ----- engine --------------------------------------------------- #
        engine = create_engine(config, self.runtime)
        t0 = time.perf_counter()
        frame_output = engine.infer_frames(spect, reporter)
        timing["model_load_and_inference"] = time.perf_counter() - t0

        # ----- postprocessing ------------------------------------------- #
        t0 = time.perf_counter()
        post = build_postprocessor(config.dbn)
        raw = post.process(frame_output, reporter)
        timing["postprocess"] = time.perf_counter() - t0

        # ----- validation ----------------------------------------------- #
        t0 = time.perf_counter()
        reporter.started(EventStage.VALIDATION, "Validating result")
        report = self.validator.validate(raw, probe)
        for issue in report.issues:
            if issue.level == "warning":
                reporter.warning(EventStage.VALIDATION, issue.message, code=issue.code)
            elif issue.level == "info":
                reporter.info(EventStage.VALIDATION, issue.message, code=issue.code)
        timing["validation"] = time.perf_counter() - t0
        reporter.completed(
            EventStage.VALIDATION,
            "ok" if report.ok else "issues found",
            issues=[i.message for i in report.issues],
        )

        # ----- derived: tempo + rhythm ---------------------------------- #
        t0 = time.perf_counter()
        reporter.started(EventStage.TEMPO, "Computing tempo estimate")
        beats_list = [float(x) for x in np.asarray(raw.beats).tolist()]
        downs_list = [float(x) for x in np.asarray(raw.downbeats).tolist()]
        tempo = self.tempo.analyze(beats_list)
        timing["tempo"] = time.perf_counter() - t0
        reporter.completed(
            EventStage.TEMPO,
            (
                f"~{tempo.bpm:.2f} BPM (median IBI)"
                if tempo.bpm is not None
                else "No tempo (insufficient beats)"
            ),
            bpm=tempo.bpm,
            method=tempo.method,
        )

        t0 = time.perf_counter()
        reporter.started(EventStage.RHYTHM, "Computing rhythm descriptors")
        rhythm = self.rhythm.analyze(beats_list, probe.duration_sec)
        timing["rhythm"] = time.perf_counter() - t0
        reporter.completed(EventStage.RHYTHM, "done")

        # ----- beat numbering ------------------------------------------- #
        beat_numbers = infer_beat_numbers(beats_list, downs_list)

        # ----- result object -------------------------------------------- #
        engine_info = engine.info
        result = BeatAnalysisResult(
            audio=probe,
            engine={
                "name": engine_info.name,
                "display_name": engine_info.display_name,
                "version": engine_info.version,
                "checkpoint": engine_info.checkpoint,
                "device": engine_info.device,
                "postprocessor": raw.postprocessor,
            },
            config={
                "checkpoint": config.checkpoint,
                "dbn": config.dbn,
                "float16": config.float16,
                "device": self.runtime.device,
            },
            beats=beats_list,
            downbeats=downs_list,
            beat_numbers=beat_numbers,
            tempo=tempo,
            rhythm=rhythm,
            timing=timing,
            validation=report.to_dict(),
            fps=frame_output.fps,
            activations=(
                {
                    "beat_logits": raw.beat_logits,
                    "downbeat_logits": raw.downbeat_logits,
                }
                if config.want_activations
                else None
            ),
        )
        result.counts = {
            "beats": len(beats_list),
            "downbeats": len(downs_list),
        }

        # ----- artifacts ------------------------------------------------ #
        t0 = time.perf_counter()
        artifacts = self.artifacts.generate(
            job_id=job_id,
            original_filename=audio_input.original_filename,
            result=result,
            reporter=reporter,
            want_beats_file=config.want_beats_file,
            want_json=config.want_json,
            want_activations=config.want_activations,
        )
        result.artifacts = artifacts
        timing["artifacts"] = time.perf_counter() - t0

        timing["total"] = time.perf_counter() - t_total
        reporter.completed(
            EventStage.RESULT,
            f"Analysis complete: {len(beats_list)} beats, "
            f"{len(downs_list)} downbeats"
            + (f", ~{tempo.bpm:.1f} BPM" if tempo.bpm else ""),
            beats=len(beats_list),
            downbeats=len(downs_list),
            bpm=tempo.bpm,
            total_ms=timing["total"] * 1000,
        )
        return result
