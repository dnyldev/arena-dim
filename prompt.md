```
I'll thoroughly explore the official Beat This! repository structure, code, and documentation.Next I'll inspect the model architecture and postprocessor in detail.# Beat This! — Technical Research Package  
**Source of Truth for Implementation**  
**Role:** Senior Research Engineer / Repository Analyst  
**Target consumer:** Coding model that must implement a full CPU-only operational dashboard without model weights, without real inference, and without guessing.

**Repository analyzed:** https://github.com/CPJKU/beat_this  
**Analysis date basis:** main branch (version 1.1.0, commit tree `b95c8ab0…`), README, pyproject.toml, full inference/model/postprocessor/preprocessing/cli/utils source, CHANGELOG, LICENSE, hubconf, tests, example notebook.  
**Status labels used throughout:**  
- **VERIFIED** — directly observed in code/docs  
- **INFERRED** — logical conclusion from code, not explicitly stated  
- **UNKNOWN** / **NOT TESTABLE WITHOUT MODEL WEIGHTS**

---

## 1. Complete Repository Identification

| Field | Value | Status |
|-------|--------|--------|
| Name | beat_this (PyPI: `beat-this`) | VERIFIED |
| Display title | Beat This! | VERIFIED |
| URL | https://github.com/CPJKU/beat_this | VERIFIED |
| Owner | CPJKU (Institute of Computational Perception, JKU Linz) | VERIFIED |
| License | MIT | VERIFIED |
| Version | 1.1.0 (pyproject.toml + CHANGELOG 2026-04-14) | VERIFIED |
| Paper | Foscarin, Schlüter, Widmer — ISMIR 2024 “Beat This! Accurate Beat Tracking Without DBN Postprocessing” (arXiv:2407.21658) | VERIFIED |
| Related | Annotations: https://github.com/CPJKU/beat_this_annotations ; Spectrograms Zenodo 13922116 | VERIFIED |

### Directory Structure (complete, recursive)

```
beat_this/                          # root
├── .github/workflows/pypi.yml
├── .gitignore
├── CHANGELOG.md
├── LICENSE                         # MIT
├── README.md
├── beat_this_example.ipynb         # Colab demo
├── hubconf.py                      # torch.hub entry
├── pyproject.toml                  # package metadata + CLI entry
├── requirements.txt                # pinned known-good inference deps
├── beat_this/                      # Python package
│   ├── __init__.py                 # empty
│   ├── cli.py                      # CLI entry (beat_this command)
│   ├── inference.py                # core inference API + model loading
│   ├── preprocessing.py            # audio load + LogMelSpect
│   ├── utils.py                    # beat numbering, TSV save, state_dict helpers
│   ├── dataset/                    # training only
│   │   ├── __init__.py
│   │   ├── augment.py
│   │   ├── dataset.py
│   │   └── mmnpz.py
│   └── model/
│       ├── __init__.py             # empty
│       ├── beat_tracker.py         # BeatThis NN architecture
│       ├── roformer.py             # Rotary transformer blocks
│       ├── postprocessor.py        # minimal peak-picking + optional DBN
│       ├── loss.py                 # training losses
│       └── pl_module.py            # PyTorch Lightning wrapper (training/eval)
├── launch_scripts/
│   ├── train.py
│   ├── compute_paper_metrics.py
│   ├── preprocess_audio.py
│   └── clean_checkpoints.py
└── tests/
    ├── test_inference.py
    └── It Don't Mean A Thing - Kings of Swing.mp3
```

### Important Files — Exact Roles

| File | Role | Depends on / used by |
|------|------|----------------------|
| `beat_this/cli.py` | CLI `beat_this`. Parses args, selects device, constructs `File2File`, batch processing, optional activations dump | inference, utils |
| `beat_this/inference.py` | **Main inference entry.** `load_checkpoint`, `load_model`, chunking, `Spect2Frames` / `Audio2Frames` / `Audio2Beats` / `File2Beats` / `File2File` | model.beat_tracker, model.postprocessor, preprocessing, utils |
| `beat_this/preprocessing.py` | `load_audio` (torchaudio → soundfile → madmom fallbacks), `LogMelSpect` | torchaudio, optional soundfile/madmom |
| `beat_this/model/beat_tracker.py` | `BeatThis` nn.Module (frontend + RoFormer + SumHead/Head) | roformer, rotary_embedding_torch, einops |
| `beat_this/model/roformer.py` | Attention, FeedForward, Transformer with rotary embeddings | einops, torch |
| `beat_this/model/postprocessor.py` | Frame logits → beat/downbeat times (minimal or DBN) | einops, optional madmom |
| `beat_this/utils.py` | `infer_beat_numbers`, `save_beat_tsv`, `replace_state_dict_key` | numpy |
| `pyproject.toml` | Package name, deps, console script `beat_this = beat_this.cli:main` | — |
| `hubconf.py` | torch.hub load | re-exports from inference |

### Entry Points

1. **CLI:** `beat_this` (installed via package) → `beat_this.cli:main`
2. **Python API (primary for integration):**
   - `from beat_this.inference import File2Beats, Audio2Beats, Audio2Frames, Spect2Frames, load_model, load_checkpoint`
   - `from beat_this.utils import save_beat_tsv, infer_beat_numbers`
3. **torch.hub:** via `hubconf.py`
4. Training/eval scripts under `launch_scripts/` (not needed for inference dashboard)

### Dependencies (Inference)

**From pyproject.toml (runtime):**
```
numpy>=1.20
torch>=2
torchaudio
einops
rotary-embedding-torch
soxr
```

**README additional recommended:**
- `tqdm` (optional, CLI progress only; not in pyproject)
- `ffmpeg` (system) for non-WAV via torchaudio
- Optional: `madmom` (only if `--dbn` / `dbn=True`) — install from `git+https://github.com/CPJKU/madmom.git`
- Optional fallbacks: `soundfile`

**requirements.txt (known-good pins):**
```
einops==0.8.0
numpy==1.26.4
rotary_embedding_torch==0.6.4
soxr==0.3.7
torch==2.3.1
torchaudio==2.3.1
tqdm==4.66.4
```

**Python:** `requires-python = ">=3"` (practically ≥3.9 recommended with torch 2.x).  
**No pytorch-lightning required for pure inference.**

### Installation (official)

```bash
# 1. Install PyTorch first (CPU or CUDA as desired)
# 2. pip install tqdm einops soxr rotary-embedding-torch
# 3. pip install beat-this
# OR dev: pip install https://github.com/CPJKU/beat_this/archive/main.zip
```

### Models / Checkpoints

- Auto-download from: `https://cloud.cp.jku.at/public.php/dav/files/7ik4RrBKTS273gp/{name}.ckpt`
- Cached via `torch.hub.load_state_dict_from_url` (typical location `~/.cache/torch/hub/checkpoints/beat_this-{name}.ckpt`)
- Default: `"final0"` (~78 MB)
- Small: `"small0"` (~8.1 MB) — useful for lighter CPU
- Format: PyTorch Lightning checkpoint dict with keys `hyper_parameters`, `state_dict` (prefix `model.` stripped on load)
- During inference PL is **not** used; converted to vanilla `BeatThis`

**Manual download:** https://cloud.cp.jku.at/index.php/s/7ik4RrBKTS273gp

---

## 2. Full Pipeline Reconstruction (Exact)

```
Audio file path (or waveform + sr)
        │
        ▼
[1] load_audio(path)                          # preprocessing.py
    → waveform: np.ndarray float64, shape (T,) or (T, C)
    → sr: int
    backends: torchaudio → soundfile → madmom
        │
        ▼
[2] mono mixdown if needed                    # Audio2Frames.signal2spect
    if ndim==2: signal = signal.mean(axis=1)  # average channels
        │
        ▼
[3] resample to 22050 Hz if sr != 22050       # soxr.resample
        │
        ▼
[4] torch.tensor(float32) on device
        │
        ▼
[5] LogMelSpect                               # preprocessing.py
    MelSpectrogram(sr=22050, n_fft=1024, hop_length=441,
                   f_min=30, f_max=11000, n_mels=128,
                   mel_scale="slaney", normalized="frame_length", power=1)
    → log1p(1000 * mel).T
    Output shape: (T_frames, 128)   # time × mel
    fps = 22050/441 = 50 exactly
        │
        ▼
[6] split_piece (if long)                     # inference.py
    chunk_size=1500 frames (=30 s)
    border_size=6 frames
    overlap = border*2; last chunk shifted to end (avoid_short_end=True)
    zero-pad borders
        │
        ▼
[7] BeatThis model (eval, inference_mode)     # per chunk, batch=1
    optional autocast float16
    Input:  (1, T_chunk, 128)
    Output: dict{"beat": (1,T), "downbeat": (1,T)}  # logits
        │
        ▼
[8] aggregate_prediction                      # discard borders, stitch
    overlap_mode="keep_first"
    → full-length beat_logits, downbeat_logits  (T_frames,)
        │
        ▼
[9] Postprocessor                             # model/postprocessor.py
    type="minimal" (default) or "dbn"
    → beat_times: np.ndarray seconds
    → downbeat_times: np.ndarray seconds
        │
        ▼
[10] Optional: save_beat_tsv / infer_beat_numbers
     → .beats TSV: "time\tbeat_number\n"  (1 = downbeat)
```

**Real pipeline classes (inheritance):**
```
Spect2Frames          # spect → logits
  └─ Audio2Frames     # waveform+sr → spect → logits
       └─ Audio2Beats # + Postprocessor → (beats, downbeats)
            └─ File2Beats  # path → load_audio → …
                 └─ File2File  # path → … → save .beats
```

**Note on File2File variable names (VERIFIED quirk):**
```python
downbeats, beats = super().__call__(audio_path)  # names swapped
save_beat_tsv(downbeats, beats, output_path)     # double-swap → correct order
```
`Postprocessor` and `File2Beats`/`Audio2Beats` return **`(beats, downbeats)`**. README and CLI activations path use correct names. File2File works only because of the double swap. **Implementers must return `(beats, downbeats)` and call `save_beat_tsv(beats, downbeats, path)`.**

---

## 3. Model Architecture (Complete)

**Class:** `beat_this.model.beat_tracker.BeatThis(nn.Module)`

### Components
1. **Frontend**
   - Stem: Rearrange `b t f → b f t` → BatchNorm1d(128) → add channel → Conv2d(1→stem_dim=32, k=(4,3), s=(4,1), p=(0,1)) → BN → GELU  
     Freq: 128 → 32
   - 3× Frontend blocks (each): optional PartialFTTransformer (freq then time attention) → Conv2d(dim→2*dim, k=(2,3), s=(2,1), p=(0,1)) → BN → GELU  
     Channels: 32→64→128→256; Freq: 32→16→8→4
   - Concat: `b c f t → b t (c*f)` = `b t 1024` → Linear(1024 → transformer_dim)

2. **Transformer:** `roformer.Transformer`
   - dim = transformer_dim (512 default / 128 small)
   - depth = n_layers = 6
   - heads = transformer_dim // head_dim (head_dim=32 → 16 or 4 heads)
   - RotaryEmbedding(head_dim)
   - RMSNorm, gated attention, scaled_dot_product_attention, GELU FF (mult=4)
   - residual + final RMSNorm

3. **Head**
   - **SumHead (default):** Linear(dim, 2) → split beat/downbeat; **beat = beat + downbeat** (float32, autocast disabled) so every downbeat is also a beat logit
   - **Head (ablation):** independent projections, no sum

### Defaults (final* models)
```
spect_dim=128, transformer_dim=512, ff_mult=4, n_layers=6,
head_dim=32, stem_dim=32,
dropout={"frontend": 0.1, "transformer": 0.2},
sum_head=True, partial_transformers=True
```
Small models: `transformer_dim=128`.

### I/O shapes (VERIFIED)
- Input spectrogram: `(B, T, 128)` float
- Output: `{"beat": (B, T), "downbeat": (B, T)}` raw logits (no sigmoid inside model)

### Weight loading (VERIFIED)
```python
checkpoint = load_checkpoint(path_or_name, device)  # local / URL / shortname
hparams = {k:v for k,v in checkpoint["hyper_parameters"].items()
           if k in inspect.signature(BeatThis).parameters}
model = BeatThis(**hparams)
state = replace_state_dict_key(checkpoint["state_dict"], "model.", "")
model.load_state_dict(state)
model.to(device).eval()
```
- `load_model(None)` creates untrained `BeatThis()` — **runs but useless**
- Auto-download on shortname; fails with `ValueError` if unreachable

**Without weights:** model architecture instantiable; forward pass possible with random weights; real beat quality **NOT TESTABLE WITHOUT MODEL WEIGHTS**.

---

## 4. Beat & Downbeat Production (Exact Algorithms)

### A. Neural outputs
Frame-wise **logits** at 50 fps for beat and downbeat.

### B. Minimal postprocessor (default, paper’s main claim — no DBN)

**File:** `postprocessor.py` `type="minimal"`, `fps=50`

1. Pack beat & downbeat logits → `(B, T, 2)`
2. Mask padded positions to -1000
3. Max-pool 1D kernel=7, stride=1, padding=3 (±3 frames ≈ ±60 ms; comment says ±70 ms)
4. Keep only positions that equal the local max **and** logit > 0 (i.e. prob > 0.5)
5. Per piece:
   - Extract peak frame indices
   - `deduplicate_peaks(width=1)` — merge adjacent peaks by running mean
   - Convert frames → seconds: `time = frame / fps`
   - **Snap every downbeat to nearest beat time**
   - `np.unique` downbeats
6. Return `(beat_times: np.ndarray, downbeat_times: np.ndarray)`

No tempo model, no HMM, no dynamic programming in the default path. Peak picking + local NMS + downbeat snapping only.

### C. Optional DBN (`dbn=True`)
Requires `madmom`. Uses `madmom.features.downbeats.DBNDownBeatTrackingProcessor`:
```
beats_per_bar=[3, 4],
min_bpm=55.0, max_bpm=215.0,
fps=50, transition_lambda=100
```
- Sigmoid logits → probabilities, clamp away from 0/1
- Combined activation: `[max(beat-downbeat, ε), downbeat]`
- DBN output → beat times + downbeat times (where beat number == 1)

### D. Beat numbers / .beats file
`infer_beat_numbers(beats, downbeats)`:
- Requires every downbeat ∈ beats (else ValueError)
- Handles pickup by looking at first full measure length
- Downbeats get number 1; subsequent beats count up until next downbeat

`save_beat_tsv(beats, downbeats, path)` writes:
```
1.234	1
1.850	2
2.466	3
...
```

### E. Tempo
**Not produced by the library.**  
INFERRED: can be derived as `60.0 / np.median(np.diff(beats))` if desired by the wrapper. Do **not** claim the repo outputs tempo.

### F. Activations
CLI `--activations` saves `.npy` of shape `(2, T)` = stacked beat/downbeat logits.

---

## 5. All Configurable Parameters

| Parameter | Default | Type | Range / Values | Effect | Where Defined |
|-----------|---------|------|----------------|--------|---------------|
| checkpoint_path / --model | `"final0"` | str | shortname, local path, URL | which weights | File2Beats, CLI, load_model |
| device | `"cpu"` (API) / gpu=0 (CLI) | str / int | `"cpu"`, `"cuda:N"`, or CLI `--gpu` (-1=CPU) | compute device | constructors, CLI |
| float16 / --float16 | False | bool | | autocast half precision | Spect2Frames+ |
| dbn / --dbn | False | bool | | use madmom DBN vs minimal | Audio2Beats, CLI |
| chunk_size | 1500 | int (hardcoded) | frames | inference chunk length (30 s) | split_predict_aggregate call |
| border_size | 6 | int (hardcoded) | frames | discard edges (loss max-pool) | same |
| overlap_mode | `"keep_first"` | str (hardcoded) | keep_first / keep_last | how to resolve chunk overlap | same |
| fps | 50 | int (hardcoded in Postprocessor default) | | frames→seconds | Postprocessor |
| sample_rate (target) | 22050 | int (hardcoded) | | resample target | LogMelSpect, signal2spect |
| n_fft | 1024 | hardcoded | | STFT | LogMelSpect |
| hop_length | 441 | hardcoded | | hop → 50 fps | LogMelSpect |
| n_mels | 128 | hardcoded | | mel bins | LogMelSpect |
| f_min / f_max | 30 / 11000 | hardcoded | Hz | mel range | LogMelSpect |
| log_multiplier | 1000 | hardcoded | | log1p(m * mel) | LogMelSpect |
| peak max-pool kernel | 7 | hardcoded | | NMS window | postp_minimal |
| peak threshold | logit > 0 | hardcoded | | min confidence | postp_minimal |
| DBN min_bpm / max_bpm | 55 / 215 | hardcoded (madmom call) | only if dbn | DBN tempo limits | postprocessor |
| DBN beats_per_bar | [3,4] | hardcoded | | | postprocessor |
| DBN transition_lambda | 100 | hardcoded | | | postprocessor |
| --output / -o | None | path | | output file or dir | CLI |
| --suffix | `.beats` | str | | output extension | CLI |
| --append | False | flag | | append vs replace suffix | CLI |
| --skip-existing | False | flag | | skip existing outs | CLI |
| --touch-first | False | flag | | touch empty file first (parallel) | CLI |
| --activations | False | flag | | also save logits .npy | CLI |

**Hardcoded (not user-facing in stock API):** all spectrogram / chunk / peak-picking constants.  
A production wrapper may expose a subset (model, dbn, device, float16) safely. Exposing BPM limits only makes sense when `dbn=True`.

---

## 6. CPU-ONLY Requirement

### Dependency classification

| Package | CPU? | GPU/CUDA? | Notes |
|---------|------|-----------|-------|
| numpy | CPU | — | OK |
| einops | CPU | — | OK |
| soxr | CPU | — | OK |
| rotary-embedding-torch | CPU | uses torch | OK |
| torch | both | CUDA optional | **Install CPU wheel** |
| torchaudio | both | follows torch | CPU wheel |
| tqdm | CPU | — | optional |
| madmom | CPU | — | optional, only for DBN; has own deps |
| soundfile | CPU | — | optional fallback |
| ffmpeg | system binary | — | for MP3 etc. via torchaudio |

### Strategy for final project
```bash
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu
pip install numpy einops soxr rotary-embedding-torch tqdm
pip install beat-this
# optional: soundfile
# DO NOT install madmom unless DBN UI toggle is offered and documented
# DO NOT pip install torch with default CUDA index
```

### Device handling in repo (VERIFIED)
- CLI: `if torch.cuda.is_available() and gpu >= 0: cuda:gpu else cpu`
- API default in constructors: `device="cpu"` (README examples often show `"cuda"`)
- No hard-coded `.cuda()` calls in inference path that ignore the `device` argument
- Model and tensors moved via `.to(device)`
- float16 autocast uses `device_type=self.device.type`
- CHANGELOG 1.1.0: “Support non-CUDA accelerator chips” (MPS etc. possible if torch supports them)

**For final project:** always pass `device="cpu"`. Never auto-select CUDA. No CUDA packages in requirements.

**Inference on CPU:** works (notebook explicitly says so). Performance **NOT TESTABLE WITHOUT WEIGHTS**.

---

## 7. What Cannot Be Verified Without Weights / Real Run

- Actual beat/downbeat accuracy or numerical outputs
- Peak counts, tempo estimates, edge-case behaviour on silence/noise
- Memory usage / latency on CPU for given audio length
- Whether a specific checkpoint file is uncorrupted
- Auto-download still works from the cloud URL (network/server state)
- Exact float16 numerical stability on CPU (autocast may be no-op)
- soxr/torch interaction if user passes pure torch tensor without numpy conversion
- File2File double-swap behaviour under all edge cases (logic is clear; runtime untested here)

**Can be verified statically:** imports, shapes from code, type flow, configuration, API signatures, serialization format, error paths that raise explicitly.

---

## 8. Real API & Interfaces

### 8.1 `File2Beats`
```python
File2Beats(checkpoint_path="final0", device="cpu", float16=False, dbn=False)
__call__(audio_path: str | Path) -> tuple[np.ndarray, np.ndarray]
# returns (beats_seconds, downbeats_seconds)
```
**Failures:** load_audio RuntimeError; checkpoint ValueError; shape errors inside.

### 8.2 `Audio2Beats`
```python
Audio2Beats(checkpoint_path="final0", device="cpu", float16=False, dbn=False)
__call__(signal, sr) -> tuple[np.ndarray, np.ndarray]
# signal: 1D or 2D (time[, channels]) array-like; sr: int
```

### 8.3 `Audio2Frames` / `Spect2Frames`
```python
# returns (beat_logits: Tensor[T], downbeat_logits: Tensor[T]) float32
```

### 8.4 `load_model` / `load_checkpoint`
As above. Shortname → download.

### 8.5 `save_beat_tsv(beats, downbeats, outpath)`
Creates parent dirs. Writes TSV. Requires downbeats ⊆ beats.

### 8.6 `infer_beat_numbers(beats, downbeats) -> np.ndarray[int]`

### 8.7 CLI
```
beat_this INPUTS... [--model NAME] [-o PATH] [--suffix .beats] [--append]
          [--skip-existing] [--touch-first] [--dbn | --no-dbn]
          [--gpu N] [--float16] [--activations]
```

### 8.8 Recommended integration surface for dashboard backend
```python
from beat_this.inference import File2Beats, Audio2Beats, load_model
from beat_this.utils import save_beat_tsv, infer_beat_numbers
from beat_this.preprocessing import load_audio  # optional direct use
```

**Do not depend on** dataset/*, loss, pl_module, launch_scripts for the product.

---

## 9–10. Frontend Design & UI Specification (Based Only on Real Capabilities)

### Design principles
- Light mode, soft, minimal, clean, modern, spacious, professional
- Operational dashboard, not a landing page
- Only controls that map to real parameters

### Suggested layout
```
┌─────────────┬──────────────────────────────────────────────┐
│ Sidebar     │ Main                                         │
│ • Dashboard │  [Upload zone / File picker]                 │
│ • Analyze   │  File meta: name, duration*, sr*, channels*  │
│ • Settings  │                                              │
│ • Debug     │  Configuration panel                         │
│             │  [Process button]  [Cancel if possible]      │
│             │  Live status + progress                      │
│             │  Results: beats table, downbeats, derived BPM│
│             │  Download .beats / JSON                      │
│             │  Debug / Logs panel (always visible or tab) │
└─────────────┴──────────────────────────────────────────────┘
```
\*duration/sr/channels from backend probe via torchaudio/soundfile, not from beat_this itself.

### UI Controls (only real ones)

| UI Control | Type | Default | Min/Max | User help | Backend param | Supported? |
|------------|------|---------|---------|-----------|---------------|------------|
| Audio file | File picker | — | audio/* | Select audio to analyze | path / bytes | Yes |
| Model | Select | final0 | final0, final1, final2, small0, small1, small2 (+ advanced list) | Checkpoint; small* faster/lighter on CPU | checkpoint_path | Yes |
| Use DBN postprocessing | Toggle | Off | — | madmom DBN (needs madmom installed); default is peak-picking | dbn | Yes (optional dep) |
| Device | Read-only or hidden | cpu | cpu only | Forced CPU | device="cpu" | Yes |
| Half precision | Toggle | Off | — | float16 autocast; limited benefit on CPU | float16 | Yes |
| Output format | Multi | beats+JSON | .beats, JSON | Download options | wrapper | Yes (wrapper) |
| Show activations | Toggle | Off | — | Include frame logits in result (large) | wrapper around Audio2Frames | Yes |

**Do NOT add (not supported by stock repo):**
- Min/Max BPM sliders (unless DBN on **and** you fork Postprocessor — currently hardcoded)
- Hop size / sample rate / threshold sliders
- Custom peak window
- Real-time streaming beat tracking
- Multi-track comparison beyond single file

### Derived display (wrapper-computed, honest)
- Approximate tempo: median IBI → BPM (label as “estimated from beats”)
- Beat count, downbeat count, duration
- Beat numbers via `infer_beat_numbers`

---

## 11. Audio File Handling

| Format | Support | How |
|--------|---------|-----|
| WAV | Yes | torchaudio native |
| MP3, FLAC, M4A, OGG, etc. | Yes if ffmpeg backend for torchaudio | system ffmpeg |
| Fallback | soundfile / madmom | if installed |

**Channels:** stereo/multi → mean to mono (axis=1 if time-first).  
**Sample rate:** any → soxr resample to 22050.  
**Dtype:** load as float64 then model float32.  
**Duration limits:** none in code; long files chunked every 30 s. Memory scales with audio length (full spectrogram held).  
**Corrupted files:** `RuntimeError: Could not load audio from "..."`.  
**Large files:** may OOM on CPU — wrapper should warn above e.g. 10–20 min (INFERRED threshold; not in repo).

**Frontend/backend duty:**
- Accept common audio MIME types
- Optionally convert with ffmpeg/pydub if torchaudio fails
- Probe duration/sr before run for UI
- Stream upload to backend temp file
- Clean temp files after

---

## 12. Real-Time Debug Dashboard — Spec

Backend must emit structured stage events (wrapper instrumentation around beat_this calls). Repo itself is silent (no logging).

**Stages the wrapper can honestly report:**

| Timestamp | Event | Source |
|-----------|-------|--------|
| t0 | File selected / received | wrapper |
| t0 | Meta: name, bytes, duration, sr, channels | torchaudio/sf probe |
| t1 | Audio load started/finished | load_audio |
| t2 | Resample needed? sr → 22050 | signal2spect |
| t3 | Mel spectrogram computation started/done, shape (T,128) | LogMelSpect |
| t4 | Model load started (cache hit/miss / download) | load_model |
| t5 | Chunking: N chunks of 1500 frames | split_piece |
| t6 | Inference chunk i/N | model forward |
| t7 | Aggregate logits | aggregate |
| t8 | Postprocess (minimal|dbn) | Postprocessor |
| t9 | Beat count, downbeat count, est. BPM | wrapper |
| t10 | Serialize output / write files | wrapper |
| ERROR | stage, exception type, message, traceback snippet | try/except |

Example log lines (frontend):
```
[12:31:04] File selected: song.wav (12.4 MB)
[12:31:04] Duration 214.3 s | sr=44100 | stereo → will mono+resample
[12:31:05] Audio loaded
[12:31:05] Resampled 44100 → 22050
[12:31:06] Log-mel spectrogram (10715, 128)
[12:31:06] Loading model final0 (cache hit)
[12:31:07] Inference: 8 chunks × 1500 frames
[12:31:15] Postprocess: minimal
[12:31:15] Done: 412 beats, 103 downbeats, ~115.2 BPM (median)
```

---

## 13. Proposed Final Architecture

```
┌─────────────────────────────────────────┐
│ Frontend (Next.js or Vite+React)        │
│  - Operational UI                       │
│  - File picker, settings, logs, results │
└─────────────────┬───────────────────────┘
                  │ HTTP (REST) + optional SSE/WebSocket for logs
┌─────────────────▼───────────────────────┐
│ Backend (FastAPI)                       │
│  - /api/health                          │
│  - /api/models                          │
│  - /api/analyze (multipart upload)      │
│  - /api/jobs/{id} status + logs + result│
│  - static download of .beats/json       │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│ Audio I/O layer                         │
│  - save upload, probe, validate         │
│  - optional ffmpeg normalize            │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│ Beat This integration (CPU)             │
│  File2Beats(checkpoint, device="cpu",   │
│             float16=..., dbn=...)       │
│  or Audio2Beats after custom load       │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│ Post + Output layer                     │
│  - infer_beat_numbers                   │
│  - estimated BPM                        │
│  - JSON schema + .beats TSV             │
│  - optional activations                 │
└─────────────────────────────────────────┘
```

**Process model:** one analysis job at a time or small worker queue (model is heavy on CPU). Keep model singleton in memory after first load.

---

## 14. Frontend Design Notes

- Light background (#F8FAFC / soft gray-white), subtle borders, ample whitespace
- Typography: clean sans (Inter / system)
- Primary action: single prominent “Analyze” button
- Disabled state while processing; spinner + stage text
- Results: table of beats (time, number, is_downbeat), summary cards, optional simple waveform/beat markers (canvas) if time permits — markers are nice-to-have, not required by repo
- No fake metrics, no GPU toggles, no unimplemented advanced panels

---

## 15. Output Specification

### Native library outputs
1. `beats: np.ndarray[float]` — seconds, sorted  
2. `downbeats: np.ndarray[float]` — seconds, subset of beats (after snap)  
3. Optional logits: two float arrays length T  
4. `.beats` TSV via `save_beat_tsv`

### Recommended JSON schema for dashboard (wrapper)

```json
{
  "schema_version": "1.0",
  "source_file": "song.wav",
  "audio": {
    "duration_sec": 214.32,
    "original_sr": 44100,
    "channels": 2,
    "processed_sr": 22050
  },
  "config": {
    "checkpoint": "final0",
    "device": "cpu",
    "float16": false,
    "dbn": false,
    "postprocessor": "minimal"
  },
  "fps": 50,
  "beats": [1.02, 1.55, 2.08, ...],
  "downbeats": [1.02, 3.14, ...],
  "beat_numbers": [1, 2, 3, 4, 1, ...],
  "estimated_tempo_bpm": 115.2,
  "counts": {"beats": 412, "downbeats": 103},
  "timings_ms": {
    "load": 120,
    "spectrogram": 800,
    "model_load": 50,
    "inference": 7200,
    "postprocess": 40,
    "total": 8210
  }
}
```

`estimated_tempo_bpm`: wrapper-defined as `60.0 / median(diff(beats))` when len(beats)≥2, else null.  
Label clearly as estimate.

`.beats` file format (VERIFIED):
```
<time_sec>\t<beat_number>\n
```
UTF-8 text, no header.

---

## 16. Error Analysis

| Failure | Cause | Detection | User message | Dev message | Recovery |
|---------|-------|-----------|--------------|-------------|----------|
| Missing/unreachable checkpoint | bad name, network, deleted cache | ValueError from load_checkpoint | “Could not load model ‘X’. Check network or provide local checkpoint.” | full exception + URL tried | retry; allow local path upload of .ckpt |
| Untrained model path | checkpoint_path=None | N/A | don’t expose | — | — |
| Invalid/corrupt audio | bad file | RuntimeError load_audio | “Could not read audio file. Use WAV/MP3/FLAC with ffmpeg installed.” | exception chain | re-encode tip |
| Unsupported format without ffmpeg | torchaudio backend missing | same | “Install ffmpeg for this format, or upload WAV.” | — | convert client-side |
| madmom missing + dbn=True | ImportError | on Postprocessor init | “DBN requires madmom. Disable DBN or install madmom.” | ImportError | force dbn=false |
| CUDA requested on CPU-only build | user error | device create may fail | “CPU-only build; device locked to cpu.” | — | ignore GPU |
| Empty / tiny audio | very short | few/no peaks | “No beats detected (audio too short or silent?).” | beat count 0 | — |
| Downbeats not in beats | internal snap bug / DBN oddity | ValueError infer_beat_numbers | “Internal consistency error numbering beats.” | ValueError | skip numbers; still return times |
| OOM | long file | RuntimeError/MemoryError | “Audio too long for available memory. Try shorter clip or small model.” | traceback | suggest small0, split file |
| Disk permission on output | save path | OSError | “Cannot write output.” | path | — |
| Concurrent model load race | multi-worker | various | — | lock singleton | process lock |

---

## 17. Test Plan (No Real Inference Required)

### Static
- Import `beat_this.inference`, `preprocessing`, `model.beat_tracker`, `postprocessor`, `utils`
- Instantiate `BeatThis()` and `BeatThis(transformer_dim=128)` with random weights; forward dummy `(1, 100, 128)` → keys beat/downbeat shapes `(1,100)`
- `Postprocessor(type="minimal")` on synthetic logits with clear peaks → times ≈ peak_frame/50
- `deduplicate_peaks`, `infer_beat_numbers` unit tests with handcrafted arrays
- `save_beat_tsv` roundtrip parse
- `replace_state_dict_key` unit test
- Config schema validation (Pydantic)

### Mathematical / data
- `22050/441 == 50` fps
- frames ↔ seconds: `t = f / 50`, `f = round(t * 50)`
- Chunk boundaries: for L frames, starts arithmetic; last start = L - (1500-6) when avoid_short_end
- Peak NMS kernel 7 symmetry
- BPM = 60/median(diff(beats))
- Beat number pickup logic (2-measure synthetic)
- Mono mean axis correctness (T,C) vs refuse (C,T) if you standardize

### Integration (mocked model)
- Mock `File2Beats.__call__` → fixed arrays; test API → JSON schema
- Upload endpoint with tiny WAV (generated sine) without loading real weights (inject mock)
- Error propagation: corrupt file → 400 + log line
- DBN=true without madmom → clear error
- Job status state machine: queued → running stages → done/error

### Frontend
- File picker accept + reject non-audio
- Settings bind to request payload
- Process disables controls; logs append
- Result table renders; download links work
- Error banner from API

### Optional golden (only if weights present in CI)
- Run test mp3 from repo; assert types and non-empty beats (soft assert counts)

---

## 18. CRITICAL UNKNOWN / UNVERIFIED

1. **Real numerical outputs & accuracy on CPU** — NOT TESTABLE WITHOUT MODEL WEIGHTS  
2. **Current availability of cloud checkpoint URL** — may change; provide offline .ckpt path support  
3. **CPU latency** for final0 vs small0 on typical hardware — UNKNOWN  
4. **Peak memory** vs audio duration — UNKNOWN (spectrogram is dense float)  
5. **float16 on CPU** benefit/harm — likely minimal; autocast may no-op  
6. **MPS/other accelerators** — CHANGELOG mentions support; not required for CPU-only product  
7. **Exact behaviour when all logits < 0** (no beats) — returns empty arrays (INFERRED from code path)  
8. **torchaudio backend matrix** per OS without ffmpeg — prefer documenting ffmpeg install  
9. **File2File naming quirk** under future refactors — implement clean `(beats, downbeats)` yourselves  
10. **Whether `torch.load(..., weights_only=True)` works for all published ckpts** — code tries it for torch≥2; fallback path uses hub loader without weights_only  

**Boundary:** Everything about API shapes, defaults, algorithms above is VERIFIED from source. Runtime performance and accuracy are not.

---

## 19. IMPLEMENTATION CONTRACT

```
STACK
- Python 3.10+ (recommend 3.11)
- Node 20+ 
- Frontend: React + Vite (or Next.js), TypeScript, light modern CSS (Tailwind OK)
- Backend: FastAPI + Uvicorn
- Beat engine: official package `beat-this==1.1.0` (or git main)

CPU-ONLY STRATEGY
- torch/torchaudio from https://download.pytorch.org/whl/cpu
- requirements freeze without CUDA packages
- device always "cpu"
- default model: small0 for snappiness OR final0 for quality (expose both)
- madmom NOT installed unless DBN feature explicitly shipped

REPOSITORY INTEGRATION
- Use File2Beats / Audio2Beats only for production path
- Singleton model cache keyed by (checkpoint, dbn, float16)
- Do not vendor-copy model code unless packaging requires; prefer dependency
- Allow CHECKPOINT_DIR env for offline .ckpt files named {name}.ckpt

INPUT
- Multipart audio file
- JSON options: checkpoint, dbn, float16, want_activations, want_beats_file

OUTPUT
- JSON schema §15
- Optional .beats download (save_beat_tsv)
- Optional activations .npy or base64 (careful size)

CONFIGURATION EXPOSED
- checkpoint ∈ {final0, final1, final2, small0, small1, small2}
- dbn: bool (default false)
- float16: bool (default false)
- (internal) device=cpu

UI CONTROLS
- File picker
- Model select
- DBN toggle (with dependency warning)
- float16 toggle
- Analyze button
- Live logs
- Results + downloads
- No fake BPM range sliders

DEBUG SYSTEM
- Structured stage events from backend
- Frontend log panel with timestamps
- Errors with stage + message

ERROR HANDLING
- Map §16 to HTTP 4xx/5xx + JSON {error, stage, detail}

TESTS
- §17 static + mocked integration + frontend component tests
- CI without weights must pass

FILE STRUCTURE (suggested)
project/
  frontend/
  backend/
    app/main.py
    app/api/routes.py
    app/services/beat_service.py   # wraps File2Beats
    app/services/job_manager.py
    app/schemas.py
    requirements.txt               # CPU torch pins
  README.md
  docker-compose.yml               # optional, CPU

RUN COMMANDS
  # backend
  cd backend && python -m venv .venv && source .venv/bin/activate
  pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu
  pip install fastapi uvicorn python-multipart beat-this einops soxr rotary-embedding-torch numpy tqdm soundfile
  uvicorn app.main:app --reload --port 8000

  # frontend
  cd frontend && npm i && npm run dev

WEIGHTS
- First run downloads final0/small0 automatically if network allows
- Document manual placement into torch hub cache or custom path
- App must start even if weights missing; fail clearly on Analyze
```

---

## 20. Confidence Matrix

| Component | Confidence | Evidence | Implement without runtime? |
|-----------|------------|----------|----------------------------|
| Repository structure | 100% | Git tree API + file reads | Yes |
| Package metadata / version | 100% | pyproject 1.1.0 | Yes |
| Dependencies | 100% | pyproject + requirements + README | Yes |
| CLI interface | 100% | cli.py full source | Yes |
| Python API classes | 100% | inference.py full source | Yes |
| Preprocessing (mel params) | 100% | preprocessing.py | Yes |
| Model architecture | 100% | beat_tracker.py + roformer.py | Yes |
| Weight load / URL / hparams filter | 100% | load_model/load_checkpoint | Yes (download needs net) |
| Chunking / aggregate | 100% | inference.py | Yes |
| Minimal postprocessor algorithm | 100% | postprocessor.py | Yes |
| DBN path + madmom params | 100% | postprocessor.py | Yes (optional) |
| Output .beats format | 100% | utils.py + README | Yes |
| Return order (beats, downbeats) | 100% | Postprocessor + README + tests | Yes |
| File2File name quirk | 100% | inference.py L312–315 | Yes (avoid using it) |
| CPU execution correctness | 85% | device plumbing + notebook claim | Yes codepath; quality unknown |
| Auto-download still works | 70% | URL in code; server not probed now | Provide offline fallback |
| Spectrogram shape (T,128) | 100% | code `.T` after MelSpectrogram | Yes |
| fps=50 exact | 100% | 22050/441 | Yes |
| Tempo as first-class output | N/A | not in repo | Implement as derived only |
| Frontend control set | 95% | mapped 1:1 to real params | Yes |
| Output JSON schema | 90% | designed from real fields + clear derived | Yes |
| Error modes | 90% | explicit raises + INFERRED OOM | Yes |
| Performance / memory | 0–20% | not measured | No claims |
| Accuracy | 0% | not run | No claims |

---

## Appendix A — Critical Implementation Snippets (for coder fidelity)

**Construct detector (CPU):**
```python
from beat_this.inference import File2Beats
detector = File2Beats(
    checkpoint_path="final0",  # or "small0"
    device="cpu",
    float16=False,
    dbn=False,
)
beats, downbeats = detector("/path/to/audio.wav")
```

**Save:**
```python
from beat_this.utils import save_beat_tsv, infer_beat_numbers
numbers = infer_beat_numbers(beats, downbeats)
save_beat_tsv(beats, downbeats, "out.beats")
```

**Log-mel constants (do not change if matching model):**
sr=22050, n_fft=1024, hop=441, fmin=30, fmax=11000, n_mels=128, log_multiplier=1000, power=1, mel_scale=slaney, normalized=frame_length.

**Inference chunk constants (hardcoded in library):** chunk_size=1500, border_size=6, overlap_mode="keep_first".

---

## Appendix B — What the Coding Model Must NOT Do

1. Invent DBN BPM UI unless wiring a forked Postprocessor  
2. Add GPU dependencies or default to CUDA  
3. Assume tempo/downbeat probability curves are returned (only times + optional logits)  
4. Use training stack (Lightning, datasets) in the product path  
5. Claim verified accuracy or latency numbers  
6. Depend on the example MP3 being present  
7. Swap beats/downbeats argument order when calling `save_beat_tsv`  
8. Change mel/hop parameters (weights expect exactly these features)

---

## Appendix C — Quick Re-scan Checklist (completed)

- [x] Full tree  
- [x] pyproject + requirements + LICENSE + CHANGELOG  
- [x] inference, preprocessing, cli, utils  
- [x] beat_tracker, roformer, postprocessor  
- [x] pl_module fps/chunk references  
- [x] hubconf, tests, notebook  
- [x] Checkpoint URL and model list  
- [x] CPU device paths  
- [x] Output formats  
- [x] Optional madmom  
- [x] No hidden inference entry points beyond those listed  

---

**End of Technical Research Package.**  
This document is sufficient for a coding model to build a CPU-only operational Beat This! dashboard with correct integration, honest UI, structured logging, and tests—without executing the model and without inventing behaviour.
```



 

 

```
مأموریت

تو یک Senior Staff Software Engineer / ML Systems Engineer / Audio Processing Engineer هستی.

بر اساس Technical Research Package که در ادامه این دستور در اختیار تو قرار می‌گیرد، یک پروژه کامل، production-grade و modular بساز که هسته آن یک Beat & Downbeat Analysis Engine مبتنی بر Beat This! باشد.

هدف ساخت یک demo، toy project، landing page یا پروژه سرگرمی نیست.

هدف ساخت یک موتور واقعی، قدرتمند، قابل توسعه و قابل اتکا برای تحلیل ریتم موسیقی است.

Frontend فقط interface برای کنترل موتور است.

موتور اصل پروژه است.

⸻

1. اصل طلایی پروژه

معماری را طوری طراحی کن که:

UI
 ↓
Application/API
 ↓
Analysis Orchestrator
 ↓
Audio Pipeline
 ↓
Feature Extraction
 ↓
Beat This Engine
 ↓
Post Processing
 ↓
Analysis / Validation
 ↓
Result

هر لایه باید مستقل و قابل تست باشد.

هیچ منطق مهمی نباید مستقیماً داخل UI قرار بگیرد.

هیچ منطق Beat Analysis نباید داخل API route قرار بگیرد.

هیچ منطق Audio Processing نباید داخل componentهای frontend قرار بگیرد.

⸻

2. از Research Package به عنوان Source of Truth استفاده کن

Research Package مرجع اصلی توست.

قوانین:

اگر چیزی در Research Package VERIFIED است:

دقیقاً مطابق آن implementation کن.

اگر چیزی INFERRED است:

بدون بررسی بیشتر آن را به عنوان حقیقت قطعی فرض نکن.

اگر چیزی UNKNOWN است:

آن را به شکل قابل توسعه طراحی کن ولی ادعای قطعی درباره رفتار آن نکن.

اگر چیزی اصلاً در Research Package وجود ندارد:

آن را اختراع نکن.

در صورت نیاز به تصمیم معماری، تصمیم مهندسی بگیر ولی آن را از رفتار واقعی Beat This جدا نگه دار.

⸻

3. هدف واقعی

ما نمی‌خواهیم صرفاً:

Upload → Beat This → JSON

بسازیم.

ما می‌خواهیم یک Audio Analysis Engine بسازیم که Beat This یکی از Engineهای داخلی آن باشد.

بنابراین Beat This باید پشت یک abstraction قرار بگیرد.

مثلاً:

BeatTrackerEngine

و implementation فعلی:

BeatThisEngine

به‌گونه‌ای که در آینده بتوانیم بدون بازنویسی کل سیستم اضافه کنیم:

BeatThisEngine
AlternativeBeatEngine
CustomBeatEngine
EnsembleBeatEngine

بدون تغییر اساسی در:

* API
* frontend
* result schema
* job system
* logging
* visualization
* storage

⸻

4. Modular Architecture

پروژه را به ماژول‌های واضح تقسیم کن.

حداقل مفاهیم زیر باید مستقل باشند:

AudioInput
AudioProbe
AudioLoader
AudioNormalizer
Resampler
FeatureExtractor
BeatEngine
PostProcessor
BeatValidator
TempoAnalyzer
RhythmAnalyzer
ResultBuilder
JobManager
EventLogger
ArtifactManager

نام‌ها می‌توانند با توجه به stack تغییر کنند، اما separation of concerns باید حفظ شود.

⸻

5. Beat Engine Interface

Beat This را مستقیماً در کل application پخش نکن.

یک interface مشخص ایجاد کن.

مثلاً:

class BeatEngine(Protocol):
    def analyze(
        self,
        audio: AudioInput,
        config: AnalysisConfig,
        reporter: ProgressReporter,
    ) -> BeatEngineResult:
        ...

Beat This implementation باید فقط مسئول integration با Beat This باشد.

این بخش نباید مسئول:

* HTTP
* UI
* فایل دانلود
* database
* frontend
* rendering
* logging presentation

باشد.

⸻

6. CPU-ONLY غیرقابل مذاکره است

کل پروژه باید CPU-only باشد.

قوانین:

* CUDA dependency اضافه نکن.
* GPU auto-detection نکن.
* GPU fallback logic نساز.
* .cuda() استفاده نکن.
* device همیشه cpu باشد.
* dependencyهای CUDA را وارد requirements نکن.
* Docker image نیز CPU-only باشد.
* هیچ featureای نباید برای کارکرد اصلی GPU را لازم داشته باشد.

اگر Beat This امکان GPU دارد، ما در این محصول از آن استفاده نمی‌کنیم.

CPU باید یک first-class execution target باشد، نه fallback.

⸻

7. Dependency Discipline

dependency اضافه فقط وقتی مجاز است که دلیل واقعی داشته باشد.

از dependencyهای غیرضروری پرهیز کن.

برای هر dependency مهم:

* چرا لازم است؟
* کدام ماژول استفاده می‌کند؟
* آیا جایگزین ساده‌تر وجود دارد؟

مشخص باشد.

Dependencyهای development را از runtime جدا کن.

⸻

8. Model Lifecycle

مدل نباید برای هر request دوباره load شود.

یک Model Manager بساز که:

* model را lazy-load کند
* cache کند
* از load همزمان جلوگیری کند
* lifecycle مشخص داشته باشد
* error واضح بدهد
* cache status را گزارش کند

مثلاً:

UNLOADED
   ↓
LOADING
   ↓
READY
   ↓
IN_USE
   ↓
READY

اگر checkpoint موجود نیست، application نباید crash کند.

Dashboard باید وضعیت را واضح نمایش دهد.

⸻

9. Weight Availability

این پروژه باید حتی بدون weight هم بتواند:

* start شود
* frontend را بالا بیاورد
* backend را بالا بیاورد
* health check بدهد
* configuration را validate کند
* testها را اجرا کند

اما هنگام Analyze اگر weight وجود ندارد باید failure کاملاً واضح باشد.

هیچ fake inference تولید نکن.

هیچ نتیجه ساختگی تولید نکن.

⸻

10. Configuration System

تمام configurationها را در یک configuration layer متمرکز کن.

مثلاً:

AnalysisConfig
EngineConfig
AudioConfig
PostProcessConfig
RuntimeConfig
OutputConfig
DebugConfig

از پراکنده‌کردن magic numberها در کد جلوگیری کن.

اما:

پارامترهایی که برای Beat This باید ثابت بمانند را قابل تغییر نکن.

مثلاً اگر model به spectrogram خاصی نیاز دارد، UI نباید اجازه دهد کاربر آن را خراب کند.

⸻

11. Configuration Safety

دو نوع parameter داشته باش:

Public Parameters

پارامترهایی که کاربر اجازه تغییر دارد.

Internal Parameters

پارامترهایی که engine برای correctness به آنها نیاز دارد.

مثلاً:

Public:
model
dbn
float16
output options
Internal:
sample rate
mel parameters
hop length
chunking constants
model input dimensions

کاربر نباید بتواند با یک slider سیستم را از specification مدل خارج کند.

⸻

12. Analysis Pipeline

یک orchestrator واقعی بساز.

مثلاً:

AnalysisJob
    ↓
Validate Input
    ↓
Probe Audio
    ↓
Load Audio
    ↓
Normalize
    ↓
Resample
    ↓
Feature Extraction
    ↓
Engine Initialization
    ↓
Beat Inference
    ↓
Post Processing
    ↓
Beat Validation
    ↓
Tempo Analysis
    ↓
Rhythm Analysis
    ↓
Result Construction
    ↓
Artifact Generation
    ↓
Completed

هر stage باید:

* input مشخص
* output مشخص
* error مشخص
* timing مشخص
* event مشخص

داشته باشد.

⸻

13. Event-Driven Progress System

Logging را با print() پراکنده نساز.

یک event system واقعی ایجاد کن.

مثلاً:

AnalysisEvent(
    job_id=...,
    stage="feature_extraction",
    status="started",
    progress=0.32,
    timestamp=...,
    message=...,
    metadata={...}
)

Eventها باید قابل مصرف توسط:

* frontend
* logs
* tests
* future WebSocket/SSE
* debugging

باشند.

⸻

14. Debugging باید First-Class باشد

Debug system فقط یک text log ساده نباشد.

برای هر job باید بتوانیم ببینیم:

Job
 ├── Input
 ├── Configuration
 ├── Audio metadata
 ├── Pipeline stages
 ├── Timing
 ├── Engine
 ├── Model
 ├── Postprocessing
 ├── Validation
 ├── Output
 └── Errors

مثلاً:

Audio Load          183 ms
Resampling          241 ms
Spectrogram         812 ms
Model Load          4.2 s
Inference           18.4 s
Postprocessing      31 ms
Validation          4 ms
Serialization       8 ms
--------------------------
Total               23.9 s

⸻

15. Error Architecture

Exceptionها را random handle نکن.

یک error taxonomy بساز.

مثلاً:

AudioError
ModelError
ConfigurationError
InferenceError
PostProcessingError
ValidationError
StorageError
SystemError

هر error باید داشته باشد:

code
stage
message
technical_detail
recoverable

Frontend فقط message مناسب کاربر را نمایش دهد.

Developer detail در Debug panel باقی بماند.

⸻

16. Beat Result باید Domain Object باشد

خروجی خام numpy را مستقیماً همه جا پخش نکن.

یک domain model ایجاد کن.

مثلاً:

BeatAnalysisResult
 ├── audio_metadata
 ├── engine
 ├── beats
 ├── downbeats
 ├── beat_numbers
 ├── tempo
 ├── rhythm
 ├── confidence
 ├── timing
 └── artifacts

در آینده این object باید بتواند قابلیت‌های بیشتری دریافت کند بدون breaking API.

⸻

17. Validation Layer

بعد از Beat This یک validation layer ایجاد کن.

این layer نباید Beat This را تغییر دهد.

فقط نتیجه را بررسی کند.

مواردی مثل:

* sorted بودن timestamps
* duplicate beats
* negative timestamps
* beats خارج از duration
* downbeat subset بودن
* فاصله‌های غیرممکن
* beat numbering consistency
* NaN / Inf
* empty result
* malformed output

را بررسی کن.

اگر validation fail شد:

نتیجه جعلی تولید نکن.

⸻

18. Tempo Analysis

Beat This خودش tempo output نمی‌دهد.

بنابراین tempo را به عنوان:

Derived Analysis

پیاده‌سازی کن.

نه به عنوان خروجی native Beat This.

فرمول و روش دقیقاً مطابق Research Package باشد.

Result باید تفاوت بین:

Native
Derived
Estimated

را حفظ کند.

⸻

19. Rhythm Analysis

ساختار را طوری طراحی کن که در آینده بتوانیم اضافه کنیم:

Time Signature
Beat Position
Bar Position
Tempo Changes
Tempo Stability
Beat Density
Rhythmic Pattern

اما چیزی را که Beat This واقعاً نمی‌دهد، به دروغ به آن نسبت نده.

فعلاً abstraction را بساز و قابلیت‌هایی که داده کافی دارند implement کن.

⸻

20. Output باید Versioned باشد

JSON output باید schema version داشته باشد.

مثلاً:

{
  "schema_version": "1.0",
  ...
}

هیچ breaking changeای بدون تغییر schema version انجام نشود.

⸻

21. Artifact System

خروجی‌ها را به شکل artifact مدیریت کن.

مثلاً:

AnalysisArtifact
 ├── JSON
 ├── .beats
 ├── activations.npy
 └── metadata

این باعث می‌شود در آینده خروجی‌هایی مثل:

MIDI
CSV
Beat Grid
DAW markers

را بدون خراب کردن معماری اضافه کنیم.

⸻

22. Job System

هر Analyze باید یک Job باشد.

مثلاً:

POST /analysis
      ↓
job_id
      ↓
QUEUED
      ↓
RUNNING
      ↓
COMPLETED

یا:

FAILED
CANCELLED

Job state machine واضح باشد.

هر job باید:

* id
* created_at
* started_at
* finished_at
* state
* configuration
* logs
* result
* error

داشته باشد.

⸻

23. Concurrency

چون CPU inference سنگین است، concurrency کورکورانه ایجاد نکن.

Model loading و inference را طوری طراحی کن که:

* memory منفجر نشود
* چند inference همزمان ناخواسته اجرا نشود
* model دوباره load نشود

در نسخه اول می‌توانی اجرای یک analysis سنگین در هر لحظه را انتخاب کنی، اما architecture باید قابلیت queue شدن داشته باشد.

⸻

24. Frontend

Frontend باید یک Control Center واقعی برای موتور باشد.

نه landing page.

کاربر باید بتواند:

Select Audio
      ↓
Configure
      ↓
Analyze
      ↓
Watch Pipeline
      ↓
Inspect Result
      ↓
Download Artifact

را کامل از UI انجام دهد.

⸻

25. UI قابلیت‌های واقعی

حداقل:

Audio

* File picker
* filename
* size
* duration
* sample rate
* channels
* format

Engine

* model
* postprocessor
* float16

Execution

* Analyze
* processing state
* progress
* current stage

Debug

* live events
* errors
* timings
* technical metadata

Results

* BPM estimate
* beat count
* downbeat count
* beat table
* beat numbers
* timestamps
* artifacts

⸻

26. Visualization

ظاهر مهم نیست؛ usability مهم است.

اما نتیجه باید قابل بررسی باشد.

در صورت امکان:

Timeline
───────────────────────────────
│  │  │  │  │  │  │  │  │
D  2  3  4  D  2  3  4

Beat و Downbeat را روی timeline نمایش بده.

این visualization باید از Result Domain Object تغذیه شود، نه مستقیماً از backend responseهای خام.

⸻

27. Frontend State Management

Stateهای زیر را از هم جدا نگه دار:

fileState
configurationState
jobState
progressState
resultState
debugState
errorState

از یک state object عظیم و غیرقابل نگهداری پرهیز کن.

⸻

28. No Fake Features

این قانون بسیار مهم است.

نباید:

* fake progress
* fake BPM
* fake beat result
* fake model status
* fake confidence
* fake GPU status

بسازی.

هر چیزی که UI نمایش می‌دهد باید از یک منبع واقعی بیاید.

⸻

29. Testing Strategy

بدون weight باید بخش بزرگی از پروژه تست شود.

حداقل:

Unit Tests

برای:

* audio utilities
* configuration
* validation
* tempo calculation
* beat numbering
* result schema
* artifact generation
* state machine
* event system

Engine Tests

Beat This را mock کن.

مثلاً:

MockEngine
    ↓
known beats
    ↓
pipeline
    ↓
expected result

Integration Tests

Upload
→ Job
→ Mock Engine
→ Validation
→ Result
→ Artifact

Frontend Tests

* upload
* configuration
* processing
* events
* errors
* results
* downloads

⸻

30. Mathematical Correctness

هر جایی که timestamp یا beat calculation وجود دارد، تست دقیق بنویس.

خصوصاً:

sample ↔ frame
frame ↔ second
second ↔ beat
BPM
median IBI
downbeat matching
beat numbering
chunk boundaries

از rounding تصادفی و implicit conversion پرهیز کن.

Precision را آگاهانه انتخاب کن.

⸻

31. No Silent Failure

هیچ failureای نباید silently swallow شود.

بد:

try:
    ...
except:
    pass

ممنوع.

اگر fallback داری:

Primary failed
↓
Fallback started
↓
Fallback succeeded

باید در event system ثبت شود.

⸻

32. Repository Integration

Beat This را تا جای ممکن به عنوان dependency مستقل نگه دار.

از copy کردن کد repository داخل پروژه خودداری کن مگر اینکه دلیل فنی مشخصی وجود داشته باشد.

Integration layer باید تمام coupling با Beat This را محدود کند.

هدف:

Application
     ↓
Beat Engine Interface
     ↓
Beat This Adapter
     ↓
Beat This

نه:

Application
 ↓
random imports from beat_this everywhere

⸻

33. Code Quality

کد باید:

* typed
* modular
* readable
* testable
* documented where necessary
* deterministic where possible
* explicit
* low-coupling
* high-cohesion

باشد.

از over-engineering بی‌دلیل هم خودداری کن.

معماری قدرتمند یعنی مرزهای درست، نه صدها کلاس بی‌دلیل.

⸻

34. Project Structure

ساختار نهایی را بر اساس معماری واقعی طراحی کن.

مثلاً:

project/
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── domain/
│   │   ├── engines/
│   │   │   ├── base.py
│   │   │   └── beat_this/
│   │   ├── audio/
│   │   ├── analysis/
│   │   ├── jobs/
│   │   ├── events/
│   │   ├── artifacts/
│   │   ├── schemas/
│   │   └── main.py
│   │
│   └── tests/
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── features/
│   │   ├── pages/
│   │   ├── state/
│   │   ├── api/
│   │   └── types/
│   └── tests/
│
├── docs/
├── scripts/
├── .env.example
├── README.md
└── docker-compose.yml

این فقط نمونه است؛ ساختار نهایی را بر اساس نیاز واقعی پروژه انتخاب کن.

⸻

35. Docker

اگر Docker استفاده می‌کنی:

* CPU-only
* reproducible
* minimal image
* healthcheck
* environment configuration
* volume برای weights/cache

داشته باشد.

Docker نباید CUDA را وارد کند.

⸻

36. Development Experience

کاربر باید بتواند پروژه را با حداقل مراحل اجرا کند.

مثلاً:

npm install
npm run dev

یا اگر backend جداست:

npm run dev

باید بتواند frontend و backend را طبق معماری پروژه بالا بیاورد.

Developer setup باید واضح باشد.

⸻

37. Health System

Backend باید endpoint سلامت داشته باشد.

مثلاً:

/api/health

و وضعیت:

API
Audio subsystem
Beat This
Model availability
Weight availability
CPU runtime

را بتواند گزارش کند.

⸻

38. Model Status در Dashboard

Dashboard باید بتواند بفهمد:

Model:
final0
Status:
READY
Device:
CPU
Weights:
AVAILABLE
Cache:
LOCAL

یا:

Weights:
MISSING
Action:
Provide checkpoint / download

بدون fake status.

⸻

39. Performance

بدون benchmark واقعی عدد نساز.

اما architecture را برای performance آماده کن:

* model caching
* lazy loading
* avoid duplicate audio decode
* avoid unnecessary copies
* avoid unnecessary serialization
* reuse model
* bounded concurrency
* chunk-aware processing
* cleanup temporary files

⸻

40. Resource Safety

برای فایل‌های بزرگ:

* temporary directory
* cleanup
* size validation
* duration metadata
* memory-conscious processing

را در نظر بگیر.

ولی thresholdهایی که از repository نمی‌آیند را به عنوان حقیقت Beat This معرفی نکن.

اگر threshold application-level تعیین کردی، configuration باشد.

⸻

41. Security پایه

حتی اگر پروژه local است:

* filename را trust نکن
* path traversal جلوگیری شود
* upload محدود شود
* temp file cleanup شود
* arbitrary path execution نداشته باش
* command injection از filename جلوگیری شود

اگر ffmpeg اجرا می‌کنی، ورودی را امن handle کن.

⸻

42. Documentation

README باید واقعاً کاربردی باشد.

شامل:

What it is
Architecture
Requirements
Installation
Running
Model weights
CPU-only setup
Dashboard
Configuration
Debugging
Testing
Output format
Troubleshooting

همچنین architecture diagram متنی داشته باش.

⸻

43. مهم‌ترین قانون پیاده‌سازی

اول معماری، بعد implementation.

قبل از نوشتن حجم زیادی کد:

1. Research Package را کامل بخوان.
2. dependency graph بساز.
3. domain model تعریف کن.
4. engine interface تعریف کن.
5. pipeline stages تعریف کن.
6. event system تعریف کن.
7. API contract تعریف کن.
8. سپس implementation را شروع کن.

⸻

44. اگر با تناقض مواجه شدی

اگر بین:

* Research Package
* README
* repository source
* dependency behavior

تناقض دیدی، silently یکی را انتخاب نکن.

آن را ثبت کن.

سپس بر اساس قوی‌ترین evidence تصمیم بگیر.

⸻

45. هیچ Runtime Dependency ساختگی

اگر package یا APIای مطمئن نیستی:

اختراع نکن.

به جای:

from beat_this import magical_function

که وجودش مشخص نیست، از APIهای VERIFIED استفاده کن.

⸻

46. کیفیت نهایی مورد انتظار

پروژه باید وقتی تحویل داده می‌شود:

* قابل اجرا باشد
* architecture واقعی داشته باشد
* modular باشد
* CPU-only باشد
* تست داشته باشد
* error handling داشته باشد
* debug داشته باشد
* frontend عملیاتی داشته باشد
* model lifecycle صحیح داشته باشد
* result schema پایدار داشته باشد
* Beat This integration تمیز داشته باشد
* بدون weight هم بتواند startup و test انجام دهد
* با weight واقعی در محیط مناسب آماده inference باشد

⸻

47. معیار موفقیت

من دنبال یک پروژه‌ای نیستم که فقط:

«کار می‌کند.»

من پروژه‌ای می‌خواهم که بتوانم بعداً روی آن ده‌ها قابلیت جدید بسازم بدون اینکه هسته خراب شود.

مثلاً:

Current
    Beat This
       ↓
Future
    ├── Better Beat Engine
    ├── Downbeat Engine
    ├── Tempo Engine
    ├── Rhythm Engine
    ├── Time Signature
    ├── Chord Engine
    ├── Stem-aware Analysis
    ├── Ensemble Engine
    └── Custom ML Models

معماری باید از چنین آینده‌ای پشتیبانی کند.

⸻

48. اما از آینده بیش از حد کدنویسی نکن

قابلیت‌های آینده را با abstraction درست آماده کن؛ اما implementation خیالی آنها را نساز.

یعنی:

درست:

BeatEngine

غلط:

BeatEngine + 15 مدل خیالی که فعلاً استفاده نمی‌شوند

⸻

49. تحویل نهایی

در پایان باید موارد زیر وجود داشته باشد:

Source Code

پروژه کامل.

Tests

تست‌های واقعی و قابل اجرا بدون weight.

README

راهنمای کامل.

Architecture Documentation

شرح معماری.

Configuration Documentation

تمام configurationها.

API Documentation

endpointها و schemaها.

Debug Documentation

نحوه مشاهده و تفسیر eventها.

Known Limitations

مواردی که بدون weight یا runtime واقعی قابل تأیید نیستند.

⸻

50. Final Self-Audit

قبل از اعلام اتمام پروژه، خودت را مجبور کن این موارد را بررسی کنی:

[ ] آیا Beat This فقط در یک integration layer قرار دارد؟
[ ] آیا UI به engine coupling ندارد؟
[ ] آیا backend به frontend coupling ندارد؟
[ ] آیا CPU واقعاً تنها execution target است؟
[ ] آیا CUDA dependency وارد نشده؟
[ ] آیا model دوباره برای هر request load نمی‌شود؟
[ ] آیا weight نبودن باعث crash startup نمی‌شود؟
[ ] آیا هیچ fake result وجود ندارد؟
[ ] آیا هیچ parameter خیالی به UI اضافه نشده؟
[ ] آیا timestampها تست شده‌اند؟
[ ] آیا beat numbering تست شده؟
[ ] آیا output schema versioned است؟
[ ] آیا errorها قابل ردیابی‌اند؟
[ ] آیا هر stage event تولید می‌کند؟
[ ] آیا testها بدون weight اجرا می‌شوند؟
[ ] آیا integration با Beat This مطابق Research Package است؟
[ ] آیا فایل‌های temporary cleanup می‌شوند؟
[ ] آیا concurrent inference کنترل شده؟
[ ] آیا پروژه قابل توسعه برای engineهای آینده است؟
[ ] آیا README از صفر قابل دنبال کردن است؟

اگر هر مورد جوابش No است، قبل از تحویل اصلاحش کن.

⸻

دستور نهایی

کد را به شکل یک demo سریع تولید نکن.

مانند یک محصول مهندسی واقعی با آن رفتار کن.

اول correctness.

بعد architecture.

بعد reliability.

بعد observability.

بعد testability.

بعد performance.

و در نهایت UI.

ظاهر زیبا امتیاز است؛ اما هسته قدرتمند، دقیق، modular و قابل اعتماد الزام است.

اگر بین «ظاهر زیباتر» و «معماری بهتر» مجبور به انتخاب شدی، همیشه معماری بهتر را انتخاب کن.

هدف نهایی:

ساخت یک Production-Grade Modular Audio Beat Analysis Engine که Beat This! را به‌عنوان اولین موتور داخلی خود استفاده می‌کند و بتواند در آینده به یک پلتفرم حرفه‌ای تحلیل موسیقی تبدیل شود.

شروع کن.
```