# Beat Analysis Engine

A production-grade, **CPU-only**, modular beat & downbeat analysis engine
powered by [Beat This!](https://github.com/CPJKU/beat_this) (Foscarin,
Schlüter, Widmer — ISMIR 2024).

The frontend is a thin control center. The real product is the engine:
a layered, event-driven pipeline with a swappable beat-engine interface,
a model lifecycle manager, typed domain objects, validation, derived
tempo/rhythm analysis, an artifact system, and a job queue.

> **Status:** the architecture, API, tests, dashboard, and Beat This!
> adapter are complete and run without model weights. Real inference
> additionally requires the `beat-this` package, CPU PyTorch, and a
> checkpoint. The application starts and serves health/configuration
> endpoints even when none of those are installed.

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│ Frontend (React + Vite + TypeScript)                             │
│  File picker · Config · Live pipeline · Results · Timeline       │
└─────────────────────────────┬────────────────────────────────────┘
                              │ HTTP/REST + SSE
┌─────────────────────────────▼────────────────────────────────────┐
│ FastAPI application layer                                        │
│  /api/health · /api/models · /api/analysis · /api/jobs/...       │
└─────────────────────────────┬────────────────────────────────────┘
                              │
┌─────────────────────────────▼────────────────────────────────────┐
│ Analysis Orchestrator (pipeline stages + timing + events)        │
│  validate → probe → load → mono → resample → mel-spect →        │
│  engine → postprocess → validate → tempo → rhythm → artifacts    │
└───────┬───────────────┬───────────────┬───────────────┬──────────┘
        │               │               │               │
┌───────▼──────┐ ┌──────▼──────┐ ┌──────▼──────┐ ┌──────▼──────┐
│ Audio layer  │ │ Features    │ │ BeatEngine  │ │ Postprocess │
│ soundfile /  │ │ LogMelSpec  │ │ (Protocol)  │ │ minimal/DBN │
│ ffmpeg       │ │ (torchaudio)│ │             │ │             │
└──────────────┘ └─────────────┘ └──────┬──────┘ └─────────────┘
                                        │
                              ┌─────────▼─────────┐
                              │ BeatThisAdapter   │  ← ONLY file
                              │  (model manager,  │    that imports
                              │   chunked infer)  │    beat_this
                              └─────────┬─────────┘
                                        │
                              ┌─────────▼─────────┐
                              │ beat-this package │
                              │ (BeatThis model)  │
                              └───────────────────┘
```

Every layer is independently testable. No beat-analysis logic lives in
API routes or frontend components.

> **Implementation charters:** rhythm/downbeat work is governed by [`docs/rhythm-interpretation-plan.md`](docs/rhythm-interpretation-plan.md); dashboard architecture and UI quality are governed by [`docs/frontend-architecture.md`](docs/frontend-architecture.md). Together they require immutable evidence, fully audited rules, modular feature boundaries, accessible primitives, progressive disclosure, and strict regression gates.
>
> ⚠️ **Mandatory follow-up:** GitHub Actions activation is temporarily blocked by GitHub App workflow permissions. Every future agent must read [`docs/PENDING-GITHUB-ACTIONS.md`](docs/PENDING-GITHUB-ACTIONS.md), remind the user, and resolve it when workflow permission becomes available.

### Key design rules

* **CPU is the only execution target.** `device="cpu"` is hard-coded;
  no CUDA packages, no GPU auto-detection, no `.cuda()` calls.
* **Beat This! is isolated.** A single adapter package
  (`app.engines.beat_this`) imports `beat_this`; everything else depends
  on the `BeatEngine` protocol. Adding `AlternativeBeatEngine`,
  `EnsembleBeatEngine`, etc. requires no changes to the API, frontend,
  result schema, job system, or artifact system.
* **No fake results.** Without weights, the app starts and serves
  `/api/health`; an analysis fails clearly with `DEPENDENCY_MISSING` /
  `MODEL_WEIGHTS_MISSING`. Nothing is fabricated.
* **Internal model constants are locked.** Sample rate (22050), hop
  (441 → 50 fps), n_fft (1024), n_mels (128), f_min (30), f_max
  (11000), chunk size (1500), border (6), peak kernel (7) match the
  published weights and are **not** exposed as user parameters.
* **Everything is observable.** Each stage emits structured
  `AnalysisEvent`s consumed by the dashboard, SSE stream, server logs,
  and tests.

---

## Repository layout

```
arena-dim/
├── backend/
│   ├── app/
│   │   ├── api/             # FastAPI routes
│   │   ├── core/            # config, error taxonomy
│   │   ├── domain/          # domain dataclasses (AudioInput, Result, Job)
│   │   ├── engines/
│   │   │   ├── base.py      # BeatEngine protocol
│   │   │   └── beat_this/   # the ONLY adapter to the beat-this package
│   │   ├── audio/           # probing, decoding, mono, resample
│   │   ├── features/        # log-mel spectrogram
│   │   ├── analysis/        # orchestrator, validator, tempo, rhythm
│   │   ├── postprocess/     # minimal peak picker + optional DBN
│   │   ├── jobs/            # job state machine + bounded worker queue
│   │   ├── events/          # structured event bus + JobReporter
│   │   ├── artifacts/       # JSON / .beats / .npy writers
│   │   ├── storage/         # secure temp-file handling
│   │   ├── schemas/         # Pydantic API schemas
│   │   └── main.py          # FastAPI factory
│   ├── tests/               # unit + integration (run without weights)
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/                # React + Vite + TS + Tailwind dashboard
├── docs/                    # architecture, API, configuration, debugging
├── scripts/                 # run_backend.sh, run_frontend.sh
├── docker-compose.yml
└── .env.example
```

---

## Quick start

### Prerequisites

* Python ≥ 3.10 (developed on 3.11)
* Node ≥ 20
* For real inference: CPU PyTorch + torchaudio, `beat-this`, and a
  checkpoint (see [Model weights](#model-weights)).
* For MP3/M4A decoding: `ffmpeg` on the host (WAV/FLAC work via
  `soundfile`/libsndfile without ffmpeg).

### 1. Backend

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate

# CPU-only PyTorch — install BEFORE beat-this so no CUDA wheel is pulled.
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu

# Remaining dependencies
pip install -r requirements.txt
# For development/tests:
pip install -r requirements-dev.txt

uvicorn app.main:app --reload --port 8000
```

Or use the helper:

```bash
./scripts/run_backend.sh
```

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Or:

```bash
./scripts/run_frontend.sh
```

Open http://localhost:5173. The Vite dev server proxies `/api` to the
backend.

### Docker (CPU-only)

```bash
docker compose up --build
# backend on :8000, frontend on :5173
```

The backend image installs PyTorch from the CPU index and `ffmpeg` /
`libsndfile`; no CUDA libraries are included.

---

## Model weights

On first analysis with a known checkpoint (`final0`, `final1`,
`final2`, `small0`, `small1`, `small2`) the adapter downloads from the
official CPJKU cloud:

```
https://cloud.cp.jku.at/public.php/dav/files/7ik4RrBKTS273gp/<name>.ckpt
```

Weights are cached via `torch.hub` (typically
`~/.cache/torch/hub/checkpoints/beat_this-<name>.ckpt`). To run fully
offline, place `<name>.ckpt` in the directory given by
`CHECKPOINT_DIR` (default `./data/checkpoints`).

| Checkpoint  | Size | transformer_dim | Notes                              |
|-------------|------|-----------------|------------------------------------|
| `final0/1/2`| ~78 MB | 512           | Full models                        |
| `small0/1/2`| ~8 MB  | 128           | Lighter, faster on CPU             |

The dashboard `/api/models` endpoint reports per-checkpoint status
(unloaded / loading / ready / in_use / failed / unavailable), whether
weights are cached, and any import/load error — **without faking it**.

---

## Configuration

All configuration is environment-driven for deployment; per-analysis
options are sent in the request. See
[`docs/configuration.md`](docs/configuration.md) for the full list.

### Public per-analysis parameters

| Field              | Default  | Meaning                                              |
|--------------------|----------|------------------------------------------------------|
| `checkpoint`       | `final0` | Short name, local path, or URL to a `.ckpt`          |
| `dbn`              | `false`  | Use optional DBN postprocessor (needs madmom)        |
| `float16`          | `false`  | Autocast half precision (limited benefit on CPU)     |
| `want_beats_file`  | `true`   | Produce `.beats` TSV                                 |
| `want_json`        | `true`   | Produce `result.json`                                |
| `want_activations` | `false`  | Include per-frame logits as `.npy`                   |
| `rhythm_interpretation_mode` | `observe_only` | `off`, fully audited observation, or conservative role interpretation |

### Internal / locked parameters

Sample rate, hop, FFT size, mel bins, mel range, log multiplier, chunk
size, border size, peak-pool kernel, and DBN constants are fixed by the
model weights and are not exposed to the user.

---

## Output

A completed job returns a versioned JSON object
(`schema_version: "1.0"`) containing:

* `audio` — probed duration/sr/channels and the processed sample rate
* `engine` — engine name, version, checkpoint, device, postprocessor
* `config` — the public configuration used
* `fps` (50), `beats[]`, `downbeats[]`, `beat_numbers[]`
* `tempo` — **derived** as `60 / median(IBI)`; origin marked `derived`
* `rhythm` — beat density, mean/std IBI, irregularity
* `counts`, `validation` (issues + ok flag), `timing_ms`
* `artifacts` — paths/keys for downloadable outputs

`.beats` files are TSV (`<time_sec>\t<beat_number>\n`, no header).
Tempo is clearly labelled as derived because Beat This! does not output
it natively.

---

## Testing

Tests run **without model weights and without the `beat-this` package**.
A mock engine and stub feature extractor exercise the full pipeline.

```bash
cd backend && source .venv/bin/activate && pytest -q
cd ../frontend && npm test
```

Coverage includes:

* unit tests for configuration, event bus, chunking/aggregation,
  peak picking, tempo/rhythm math, validator, beat numbering, storage
  security
* integration tests for the orchestrator (mock engine) and the full
  HTTP API (upload → job → events → result → artifact download)
* a frontend component test for the beat timeline

---

## Debugging & observability

Every pipeline stage emits structured events visible in:

* the dashboard **Pipeline** panel (stage list + live log),
* the SSE stream `GET /api/jobs/{id}/events/stream`,
* the events endpoint `GET /api/jobs/{id}/events`,
* server logs under the `beat_engine.events` logger,
* the final result's `timing_ms` breakdown.

Each event has `job_id`, `stage`, `status`, `timestamp`, `message`,
optional `progress`/`elapsed_ms`, and free-form `metadata`.

See [`docs/debugging.md`](docs/debugging.md) for a walkthrough.

---

## Known limitations / unverified without runtime

* **Real accuracy/latency** is not claimed; the model must be run with
  real weights to measure either.
* **Checkpoint download availability** depends on the CPJKU cloud
  server; offline placement is supported and recommended.
* **float16 on CPU** is largely a no-op in PyTorch; the flag is
  honored but benefits are unknown.
* **Memory vs audio duration** scales with the dense spectrogram; very
  long files may need splitting at the application level.
* **DBN** requires the CPJKU `madmom` fork; the default minimal peak
  picker has no extra dependency.

---

## License

MIT (see `LICENSE`). Beat This! itself is MIT © CPJKU.
