"""Engine factory.

Given a checkpoint/engine name and runtime configuration, construct a
:class:`BeatEngine`.  Only ``beat_this`` is implemented today, but the
factory is the single place to register future engines.
"""

from __future__ import annotations

from app.core.config import AnalysisConfig, RuntimeConfig
from app.core.errors import ConfigurationError
from app.engines.base import BeatEngine
from app.engines.beat_this import BeatThisAdapter, BeatThisModelManager


def create_engine(
    config: AnalysisConfig,
    runtime: RuntimeConfig,
    manager: BeatThisModelManager | None = None,
) -> BeatEngine:
    if manager is None:
        from app.engines.beat_this import get_model_manager

        manager = get_model_manager(runtime)
    # In future: dispatch on an "engine" field in AnalysisConfig.
    if config.checkpoint.startswith(("http://", "https://")) or "/" in config.checkpoint:
        # Allow arbitrary local path / URL through to Beat This.
        pass
    return BeatThisAdapter(
        checkpoint=config.checkpoint,
        manager=manager,
        float16=config.float16,
    )


def available_engine_names() -> list[str]:
    return ["beat_this"]
