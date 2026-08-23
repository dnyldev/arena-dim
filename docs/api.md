# HTTP API

Base URL: `http://localhost:8000`

Interactive OpenAPI docs: `GET /docs` (Swagger UI) and `/redoc`.

## System

### `GET /api/health`

Reports subsystem status.

```json
{
  "status": "ok",
  "version": "1.0.0",
  "device": "cpu",
  "cpu_only": true,
  "audio_backends": ["soundfile", "ffmpeg"],
  "beat_this_installed": true,
  "models": [ { "checkpoint": "final0", "engine_status": "ready", ... } ],
  "uptime_sec": 42.1
}
```

### `GET /api/spec`

Returns the locked model constants (sample rate, hop, mel bins, fps,
chunk size, known checkpoints) so the UI can display them without
hard-coding.

### `GET /api/models` · `GET /api/models/{checkpoint}`

Per-checkpoint status including `engine_status`, `weights_available`,
`weights_source` (`local` / `downloadable` / `missing`),
`beat_this_installed`, and any `import_error` / `load_error`.

### `POST /api/models/preload/{checkpoint}`

Eagerly loads a checkpoint into the cache. Returns 503 when
`beat-this` is missing and 502 when the checkpoint cannot be loaded.

## Analysis

### `POST /api/analysis`

Multipart form upload.

| Field   | Type   | Required | Notes                                   |
|---------|--------|----------|-----------------------------------------|
| `audio` | file   | yes      | Any audio the backend can decode        |
| `config`| string | no       | JSON `AnalysisConfig` (see configuration)|

Returns a `Job`:

```json
{
  "id": "9f1c…",
  "state": "queued",
  "created_at": 1787367150.9,
  "config": { "checkpoint": "final0", "dbn": false, "float16": false },
  "input": "song.wav",
  "result": null,
  "error": null
}
```

### `GET /api/jobs/{id}`

Returns the current `Job`. In terminal states `result` or `error` is
populated.

### `GET /api/jobs?limit=50`

Recent jobs (newest first).

### `POST /api/jobs/{id}/cancel`

Requests cancellation of a queued/running job.

### `GET /api/jobs/{id}/events`

All recorded `AnalysisEvent`s for the job (see debugging).

### `GET /api/jobs/{id}/events/stream`

Server-Sent Events stream. Each `data:` line is a JSON event. The
stream closes after a `job/completed` or `job/failed` event. Sends a
15-second keepalive comment.

### `GET /api/jobs/{id}/artifacts/{name}`

Download a produced artifact. `name` is one of `json`, `beats`,
`activations`, `meta` (only those produced are available).

## Result schema (`schema_version = "1.0"`)

```json
{
  "schema_version": "1.0",
  "audio": {
    "duration_sec": 214.32,
    "original_sr": 44100,
    "channels": 2,
    "processed_sr": 22050,
    "format": "WAV",
    "codec": "PCM_16"
  },
  "engine": {
    "name": "beat_this",
    "display_name": "Beat This!",
    "version": "1.1.0",
    "checkpoint": "final0",
    "device": "cpu",
    "postprocessor": "minimal"
  },
  "config": { "checkpoint": "final0", "dbn": false, "float16": false, "device": "cpu" },
  "fps": 50.0,
  "beats": [1.02, 1.55, 2.08],
  "downbeats": [1.02],
  "beat_numbers": [1, 2, 3],
  "tempo": {
    "bpm": 115.2,
    "origin": "derived",
    "method": "median_ibi",
    "median_ibi_sec": 0.521,
    "min_bpm": 110.0,
    "max_bpm": 120.0,
    "curve_window_beats": 8,
    "curve": [
      { "time_sec": 3.2, "bpm": 114.8 },
      { "time_sec": 3.7, "bpm": 115.1 },
      { "time_sec": 4.2, "bpm": 118.4 }
    ]
  },
  "meter": {
    "beats_per_bar": 4,
    "origin": "estimated",
    "method": "downbeat_interval_mode",
    "confidence": 0.97,
    "per_bar": [4, 4, 4, 4, 3, 4],
    "is_stable": true
  },
  "rhythm": {
    "beat_density_beats_per_second": 1.92,
    "mean_ibi_sec": 0.52,
    "std_ibi_sec": 0.01,
    "irregularity": 0.02
  },
  "counts": { "beats": 412, "downbeats": 103 },
  "timing_ms": {
    "probe": 5, "audio_prepare": 120, "spectrogram": 800,
    "model_load_and_inference": 7200, "postprocess": 40,
    "validation": 4, "tempo": 1, "rhythm": 1, "meter": 1, "artifacts": 8,
    "total": 8210
  },
  "validation": { "ok": true, "issues": [] },
  "artifacts": { "json": "/…/result.json", "beats": "/…/song.beats" }
}
```

## Error format

```json
{
  "error": {
    "code": "MODEL_WEIGHTS_MISSING",
    "stage": "model",
    "message": "Checkpoint 'final0' is not available locally…",
    "technical_detail": "checkpoint_dir=…, allow_download=False",
    "recoverable": true
  }
}
```

Common HTTP mappings: 400 (bad config / audio), 404 (unknown job /
artifact), 409 (invalid job state), 429 (queue full / upload too
large), 502 (model load failed), 503 (dependency/weights missing).
