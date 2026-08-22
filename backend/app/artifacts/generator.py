"""Artifact generation.

Produces the downloadable outputs of an analysis:

* ``result.json`` — public schema (versioned),
* ``<name>.beats`` — tab-separated ``<time>\\t<number>\\n`` via the
  beat_this helper when available, otherwise a TSV of time + number,
* ``activations.npy`` — optional stacked (2, T) logits (large),
* ``meta.json`` — run metadata (engine, config, timing).

Artifacts are written under the runtime artifact directory in a
per-job subfolder.  Adding future formats (MIDI, CSV, DAW markers) is
a matter of extending this class without touching the pipeline.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

from app.core.errors import ArtifactError
from app.core.config import RuntimeConfig
from app.domain.models import BeatAnalysisResult
from app.events import EventStage, JobReporter


class ArtifactGenerator:
    def __init__(self, runtime: RuntimeConfig) -> None:
        self.runtime = runtime

    def job_dir(self, job_id: str) -> Path:
        d = self.runtime.artifact_dir / job_id
        d.mkdir(parents=True, exist_ok=True)
        return d

    def generate(
        self,
        job_id: str,
        original_filename: str,
        result: BeatAnalysisResult,
        reporter: JobReporter,
        *,
        want_beats_file: bool = True,
        want_json: bool = True,
        want_activations: bool = False,
    ) -> dict[str, str]:
        out_dir = self.job_dir(job_id)
        stem = Path(original_filename).stem or "audio"
        produced: dict[str, str] = {}

        reporter.started(EventStage.ARTIFACT, "Writing artifacts")
        try:
            if want_json:
                p = out_dir / "result.json"
                p.write_text(
                    json.dumps(result.to_public_dict(), indent=2), encoding="utf-8"
                )
                produced["json"] = str(p)

            meta = {
                "engine": result.engine,
                "config": result.config,
                "audio": {
                    "duration_sec": result.audio.duration_sec,
                    "sample_rate": result.audio.sample_rate,
                    "channels": result.audio.channels,
                },
                "timing_ms": {
                    k: round(v * 1000, 3) for k, v in result.timing.items()
                },
                "validation": result.validation,
                "counts": {
                    "beats": len(result.beats),
                    "downbeats": len(result.downbeats),
                },
            }
            mp = out_dir / "meta.json"
            mp.write_text(json.dumps(meta, indent=2), encoding="utf-8")
            produced["meta"] = str(mp)

            if want_beats_file:
                p = out_dir / f"{stem}.beats"
                self._write_beats_tsv(p, result)
                produced["beats"] = str(p)

            if want_activations:
                # Only available when the engine+postprocessor exposed them.
                raw = result.activations
                if raw is not None:
                    ap = out_dir / "activations.npy"
                    beat_logits = raw.get("beat_logits")
                    down_logits = raw.get("downbeat_logits")
                    if beat_logits is not None and down_logits is not None:
                        stack = np.stack(
                            [
                                np.asarray(beat_logits, dtype=np.float32),
                                np.asarray(down_logits, dtype=np.float32),
                            ],
                            axis=0,
                        )
                        np.save(ap, stack)
                        produced["activations"] = str(ap)
        except OSError as exc:
            raise ArtifactError(
                f"Could not write artifacts: {exc}", technical_detail=str(exc)
            ) from exc

        reporter.completed(
            EventStage.ARTIFACT,
            f"Wrote {len(produced)} artifact(s)",
            artifacts=sorted(produced),
        )
        return produced

    def _write_beats_tsv(
        self, path: Path, result: BeatAnalysisResult
    ) -> None:
        beats = result.beats
        numbers = result.beat_numbers
        if len(beats) != len(numbers):
            # Fall back to all-1 numbering if inconsistent.
            numbers = [1] * len(beats)
        try:
            from beat_this.utils import save_beat_tsv as _bt_save

            _bt_save(
                np.asarray(beats, dtype=np.float64),
                np.asarray(
                    [beats[i] for i, n in enumerate(numbers) if n == 1],
                    dtype=np.float64,
                ),
                str(path),
            )
            return
        except ImportError:
            pass
        except Exception:
            # Fall through to our own writer on any beat_this issue.
            pass
        with path.open("w", encoding="utf-8") as fh:
            for t, n in zip(beats, numbers):
                fh.write(f"{t:.6f}\t{n}\n")
