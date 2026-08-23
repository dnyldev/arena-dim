from app.engines.beat_this.manager import BeatThisModelManager, get_model_manager


def _lazy_adapter():
    from app.engines.beat_this.adapter import BeatThisAdapter

    return BeatThisAdapter


def __getattr__(name):
    if name == "BeatThisAdapter":
        return _lazy_adapter()
    raise AttributeError(name)


__all__ = ["BeatThisAdapter", "BeatThisModelManager", "get_model_manager"]
