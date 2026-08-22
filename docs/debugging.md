# Debugging

The engine is built around structured events rather than scattered
`print()` calls. Every analysis is observable in four places:

1. **Dashboard Pipeline panel** — live stage list + scrolling log.
2. **SSE stream** — `GET /api/jobs/{id}/events/stream`.
3. **Events endpoint** — `GET /api/jobs/{id}/events` (full history).
4. **Server logs** — logger `beat_engine.events`.

## Event shape

```json
{
  "job_id": "9f1c…",
  "stage": "inference",
  "status": "progress",
  "timestamp": 1787367155.123,
  "message": "Chunk 3/8",
  "progress": 0.375,
  "elapsed_ms": 4120.5,
  "metadata": { "chunk": 3, "total": 8 }
}
```

* `stage` — one of: `validate`, `probe`, `audio_load`, `normalize`,
  `resample`, `feature_extraction`, `model_load`, `inference`,
  `postprocess`, `validation`, `tempo`, `rhythm`, `meter`, `artifact`,
  `result`, `job`, `system`.
* `status` — `started`, `progress`, `completed`, `failed`, `skipped`,
  `info`, `warning`.

## Typical trace

```
probe/started           Probing audio metadata
probe/completed         214.32s | 44100 Hz | 2 ch
audio_load/started      Loading song.wav
audio_load/completed    Decoded with soundfile (44100 Hz, 2 ch)
normalize/completed     Mono mixdown complete
resample/info           Resampled 44100 → 22050
feature_extraction/...  Spectrogram shape (10715, 128)
model_load/completed    Model ready (source=local)
inference/progress      Chunk 3/8 (37.5%)
inference/completed     Inference complete (7200 ms)
postprocess/completed   412 beats, 103 downbeats
validation/info         …
tempo/completed         ~115.20 BPM (median IBI)
result/completed        Analysis complete: 412 beats, 103 downbeats
job/completed           Job completed
```

## Reading the timing breakdown

`result.timing_ms` reports wall-clock per stage. `total` is the
end-to-end time including everything. `model_load_and_inference`
combines model acquisition (cache hit after the first run) with the
neural forward pass.

## Common failures

| Symptom in the UI                  | Likely cause / action                                      |
|------------------------------------|------------------------------------------------------------|
| `DEPENDENCY_MISSING` at features   | Install CPU `torch` + `torchaudio`                         |
| `MODEL_WEIGHTS_MISSING`            | Place `<name>.ckpt` in `CHECKPOINT_DIR` or enable download |
| `AUDIO_UNREADABLE`                 | Install `ffmpeg` for MP3/M4A, or upload WAV/FLAC           |
| `DEPENDENCY_MISSING` at postprocess with DBN | Install the CPJKU madmom fork                 |
| `VALIDATION_FAILED`                | Check `technical_detail`; engine produced malformed output |
| `AUDIO_TOO_LARGE`                  | Raise `MAX_UPLOAD_MB` or upload a shorter clip             |

Every error carries `stage`, `code`, `recoverable`, and a
`technical_detail` string intended for developers; the dashboard shows
the user-safe `message` and exposes the detail in its failed-job panel.

## Tailing logs locally

```bash
# Server logs
uvicorn app.main:app --log-level debug 2>&1 | grep beat_engine

# SSE from a running job
curl -N http://localhost:8000/api/jobs/$JOB/events/stream
```

## "No silent failures" policy

The codebase contains no bare `except: pass`. Any fallback (audio
backend, beat-numbering) is reported as an event/warning. If a
dependency is missing, the stage raises a typed
`DependencyMissingError` with an actionable message rather than
degrading silently.
