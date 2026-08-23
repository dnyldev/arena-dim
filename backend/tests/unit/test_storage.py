import dataclasses

import io

import pytest

from app.core.config import RuntimeConfig
from app.core.errors import AudioTooLargeError
from app.storage import UploadStorage
from app.storage.uploads import safe_filename


def test_safe_filename_strips_traversal():
    # The on-disk name must never contain path separators.
    assert "/" not in safe_filename("../../etc/passwd")
    assert "\\" not in safe_filename("..\\..\\etc\\passwd")
    assert safe_filename("/etc/passwd") == "passwd"
    # A path component separator is stripped (basename is taken), and
    # remaining unsafe characters are replaced.
    assert "/" not in safe_filename("a b/c.wav")


def test_save_and_cleanup(runtime, tmp_path):
    storage = UploadStorage(runtime)
    data = b"RIFF....WAVEfmt " + b"\x00" * 1000
    audio = storage.save_stream(io.BytesIO(data), "song.wav", "audio/wav")
    assert audio.path.exists()
    assert audio.size_bytes == len(data)
    storage.cleanup(audio)
    assert not audio.path.exists()


def test_size_limit(runtime, tmp_path):
    rt = dataclasses.replace(
        runtime,
        max_upload_mb=1,
        data_dir=tmp_path / "d",
        upload_dir=tmp_path / "d" / "u",
        artifact_dir=tmp_path / "d" / "a",
        checkpoint_dir=tmp_path / "d" / "c",
    )
    storage = UploadStorage(rt)
    data = b"x" * (2 * 1024 * 1024)
    with pytest.raises(AudioTooLargeError):
        storage.save_stream(io.BytesIO(data), "big.wav")
