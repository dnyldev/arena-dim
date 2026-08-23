# Architecture

This document describes the layers, data flow, extension points, and
design decisions of the Beat Analysis Engine.

## 1. Layered pipeline

```
UI  →  Application/API  →  Analysis Orchestrator  →  Audio pipeline
      →  Feature extraction  →  BeatEngine  →  PostProcessor
      →  Validation/Analysis  →  Artifacts
```

No layer reaches across more than one boundary:

* The **frontend** only knows the REST/SSE contract and the result
  schema. It never imports audio code, never calls Beat This!, and
  never computes beats.
* The **API layer** (`app/api/`) handles HTTP, multipart upload,
  parameter parsing, and error mapping. It contains no analysis logic.
* The **orchestrator** (`app/analysis/orchestrator.py`) wires stages,
  times them, emits events, and constructs the result. It contains no
  HTTP or file-format code.
* **Stage modules** (`audio`, `features`, `engines`, `postprocess`,
  `analysis`, `artifacts`) each do one thing and are individually
  testable.

## 2. Core domain types (`app/domain/models.py`)

| Type                  | Purpose                                            |
|-----------------------|----------------------------------------------------|
| `AudioInput`          | Server-controlled path + original filename + size  |
| `AudioProbe`          | Duration / sample rate / channels / format         |
| `AudioData`           | Decoded mono float32 at the target sample rate     |
| `Spectrogram`         | `(T, 128)` log-mel at 50 fps                       |
| `BeatEngineRawResult` | Times + optional logits from an engine             |
| `BeatAnalysisResult`  | Final domain object exposed to clients             |
| `Job`                 | Job state + config + result/error                  |
| `ValidationReport`    | Ok flag + typed issues                             |
| `TempoEstimate`       | `origin` ∈ {native, derived, estimated}            |

## 3. Beat engine interface

`app/engines/base.py` defines a small `BeatEngine` protocol:

```python
class BeatEngine(Protocol):
    info: EngineInfo
    def load(self) -> None: ...
    def unload(self) -> None: ...
    def infer_frames(self, spectrogram, reporter) -> EngineFrameOutput: ...
```

* Input: a `Spectrogram` (no audio, no files).
* Output: per-frame beat/downbeat **logits**.
* The engine does not peak-pick, tempo-analyze, or write artifacts.

`BeatThisAdapter` (`app/engines/beat_this/adapter.py`) is the **only**
module that imports `beat_this`. It:

* obtains a cached model from `BeatThisModelManager`,
* chunks the spectrogram (30 s chunks, 6-frame borders),
* runs `model(tensor)` under `torch.inference_mode()`,
* stitches predictions with `keep_first`,
* emits progress events per chunk,
* pins the device to CPU.

Adding a new engine means implementing the protocol and registering it
in `app/engines/factory.py`. No other module changes.

## 4. Model lifecycle

`BeatThisModelManager` implements:

```
UNLOADED → LOADING → READY ⇄ IN_USE → (UNLOADED | FAILED | UNAVAILABLE)
```

* Models are loaded lazily on first use.
* One model per checkpoint is cached (CPU memory is precious).
* Loading is serialized with a per-checkpoint lock; concurrent
  analyses share one model.
* A failed load records the error; it is reported via `EngineInfo`.
* Missing `beat-this` or missing weights are reported as
  `UNAVAILABLE` / `MODEL_WEIGHTS_MISSING`, never as an import-time
  crash.

## 5. Configuration tiers

* **Public** (`AnalysisConfig`): checkpoint, dbn, float16, output
  options — what the dashboard may change.
* **Internal / fixed** (`BeatThisSpec`): sample rate, hop, n_fft,
  n_mels, f_min/f_max, log multiplier, chunk/border sizes, peak kernel,
  DBN constants. These match the published weights and are locked.
* **Runtime** (`RuntimeConfig`, env-driven): directories, limits,
  concurrency, network policy.

## 6. Events and observability

`EventBus` is a thread-safe pub/sub. A `JobReporter` bound to a job id
emits `AnalysisEvent`s. Events are:

* recorded in per-job history (for the events endpoint),
* streamed to the dashboard via SSE,
* logged through Python logging,
* asserted on by tests.

Every pipeline stage reports `started`, zero or more `progress`, and
`completed`/`failed`, with elapsed milliseconds.

## 7. Job system

`JobManager` runs analyses on a bounded worker pool (default 1 — CPU
inference is heavy). Jobs transition through
`queued → running → completed|failed|cancelled`. The queue has a
maximum depth; excess submissions receive a clear error. Uploaded temp
files are removed after every run.

## 8. Error taxonomy

All errors derive from `BeatAnalysisError` and carry:
`code`, `stage`, `message`, `technical_detail`, `recoverable`.

| Code                   | When                                         |
|------------------------|----------------------------------------------|
| `INVALID_CONFIGURATION`| Bad user parameters                          |
| `AUDIO_*`              | Probe/decode/format/size problems            |
| `MODEL_*`              | Dependency / weights / load failures         |
| `INFERENCE_FAILED`     | Neural forward pass raised                   |
| `POSTPROCESSING_FAILED`| Peak picker / DBN raised                     |
| `VALIDATION_FAILED`    | Output violated invariants                   |
| `ARTIFACT_WRITE_FAILED`| Disk/serialization error                     |
| `JOB_*`                | Unknown job / invalid transition / cancelled |
| `DEPENDENCY_MISSING`   | torch / torchaudio / soundfile / madmom      |
| `INTERNAL_ERROR`       | Unexpected exception (wrapped)               |

The API maps these to HTTP 4xx/5xx with a JSON `error` body.

## 9. Validation

`BeatValidator` inspects the raw result without modifying it:

* finite / non-negative / sorted timestamps,
* no duplicates beyond snapping tolerance,
* timestamps within audio duration,
* downbeats are a subset of beats,
* plausible IBI range (warning),
* empty result is reported as info, not a hard failure.

Hard violations raise `ValidationError`; soft issues are returned in the
result's `validation.issues`.

## 10. Derived analysis

* **Tempo** — `60 / median(IBI)`; `origin = derived`, `method = median_ibi`.
  A **tempo curve** (`tempo.curve`) is also produced: a sliding window
  (default 8 beats, `tempo.curve_window_beats`) of median local BPM
  anchored at each window's center time, so genuine tempo drift is
  visible instead of collapsed into one scalar. Still `origin =
  derived` — it's a deterministic transform of native beat times.
* **Meter (time signature)** — `MeterAnalyzer` (`analysis/meter.py`)
  estimates beats-per-bar from the gaps between consecutive downbeats
  (via the same beat-numbering used for `beat_numbers`), reports the
  modal bar length, a `confidence` (fraction of bars matching the
  mode), and `is_stable` (confidence ≥ 0.9). This is explicitly
  `origin = estimated` — a heuristic, not a native model output —
  because Beat This! never outputs a time signature.
* **Rhythm** — beat density, mean/std IBI, coefficient of variation.
  Bar-position detection beyond the tempo curve and meter estimate is
  **not** fabricated; `RhythmAnalyzer` is the extension point for
  further descriptors.

## 11. Extension points

| Want to add…               | Touch only…                                          |
|----------------------------|------------------------------------------------------|
| A new beat engine          | `engines/<name>/` + register in `factory.py`         |
| A new postprocessor        | `postprocess/` (implement the protocol)              |
| A new artifact format      | `artifacts/generator.py`                             |
| A new rhythmic descriptor  | `analysis/rhythm.py`                                 |
| A meter/time-sig refinement| `analysis/meter.py`                                  |
| A new audio backend        | `audio/backends.py`                                  |
| A new API field            | schema + result builder (version the schema)         |
