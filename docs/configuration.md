# Configuration

## Environment variables (RuntimeConfig)

| Variable                   | Default                  | Purpose                                   |
|----------------------------|--------------------------|-------------------------------------------|
| `HOST`                     | `0.0.0.0`                | API bind address                          |
| `PORT`                     | `8000`                   | API port                                  |
| `LOG_LEVEL`                | `INFO`                   | Python logging level                      |
| `CORS_ORIGINS`             | `*`                      | Comma-separated allowed origins           |
| `DATA_DIR`                 | `./data`                 | Root data directory                       |
| `UPLOAD_DIR`               | `./data/uploads`         | Temporary upload storage                  |
| `ARTIFACT_DIR`             | `./data/artifacts`       | Per-job artifacts                         |
| `CHECKPOINT_DIR`           | `./data/checkpoints`     | Offline `.ckpt` files (`<name>.ckpt`)     |
| `MAX_UPLOAD_MB`            | `500`                    | Reject larger uploads                     |
| `MIN_AUDIO_SECONDS`        | `0.5`                    | Reject shorter audio                      |
| `MAX_AUDIO_SECONDS`        | `1800`                   | Application-level warning threshold       |
| `MAX_CONCURRENT_ANALYSES`  | `1`                      | CPU inference worker count                |
| `JOB_QUEUE_MAX`            | `4`                      | Maximum queued jobs                       |
| `JOB_TTL_SECONDS`          | `3600`                   | Finished-job retention for pruning        |
| `ALLOW_MODEL_DOWNLOAD`     | `true`                   | Allow auto-download of checkpoints        |
| `CHECKPOINT_BASE_URL`      | CPJKU cloud              | Base URL for downloads                    |

## Per-analysis request (`AnalysisConfig`)

Sent as JSON in the `config` form field of `POST /api/analysis`:

| Field              | Type    | Default  | Notes                                        |
|--------------------|---------|----------|----------------------------------------------|
| `checkpoint`       | string  | `final0` | Short name, local path, or http(s) URL       |
| `dbn`              | bool    | `false`  | Needs CPJKU `madmom` fork when `true`        |
| `float16`          | bool    | `false`  | Honored; limited benefit on CPU              |
| `want_beats_file`  | bool    | `true`   | Produce `.beats` TSV artifact                |
| `want_json`        | bool    | `true`   | Produce `result.json`                        |
| `want_activations` | bool    | `false`  | Stacked `(2, T)` logits as `.npy`            |

Unknown fields are rejected with `UNSUPPORTED_PARAMETER`.

## Locked model constants

These match the Beat This! weights and must not change between engines
that use those weights. They are exposed read-only by `GET /api/spec`.

| Constant         | Value                |
|------------------|----------------------|
| `sample_rate`    | 22050 Hz             |
| `hop_length`     | 441 (→ 50 fps)       |
| `n_fft`          | 1024                 |
| `n_mels`         | 128                  |
| `f_min`/`f_max`  | 30 / 11000 Hz        |
| log multiplier   | 1000                 |
| chunk size       | 1500 frames (30 s)   |
| border size      | 6 frames             |
| peak pool kernel | 7                    |
| DBN BPM range    | 55–215               |
| DBN beats/bar    | 3, 4                 |
| DBN lambda       | 100                  |

## CPU-only policy

* The runtime always uses `device="cpu"`.
* The CPU PyTorch wheel is installed from
  `https://download.pytorch.org/whl/cpu` before any dependency that
  might pull CUDA.
* The Docker image is based on `python:3.11-slim`, with no CUDA
  toolkit.
* The code contains no `.cuda()` calls and never auto-selects GPU.
