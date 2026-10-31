"""Never load unverified/partial speech artifacts and never download on import."""

import hashlib
import json
import os
import sys
from pathlib import Path

from autumn.actions.catalog import local_path, no_reparse

ARTIFACTS = {
    "voice_license": ("tts/MODEL_CARD",351,"ce49eb457742208166d399a40cdec2c7fa9db77960930031564ab56f12882645"),
    "wake": ("wake/hey_jarvis_v0.1.onnx",1271370,"94a13cfe60075b132f6a472e7e462e8123ee70861bc3fb58434a73712ee0d2cb"),
    "wake_mel": ("wake/melspectrogram.onnx",1087958,"ba2b0e0f8b7b875369a2c89cb13360ff53bac436f2895cced9f479fa65eb176f"),
    "wake_embedding": ("wake/embedding_model.onnx",1326578,"70d164290c1d095d1d4ee149bc5e00543250a7316b59f31d056cff7bd3075c1f"),
    "base.en": (
        "stt/ggml-base.en.bin",
        147964211,
        "a03779c86df3323075f5e796cb2ce5029f00ec8869eee3fdfb897afe36c6d002",
    ),
    "small.en": (
        "stt/ggml-small.en.bin",
        487614201,
        "c6138d6d58ecc8322097e0f987c32f1be8bb0a18532a3f88f734d1bbf9c41e5d",
    ),
    "voice": (
        "tts/en_US-lessac-medium.onnx",
        63201294,
        "5efe09e69902187827af646e1a6e9d269dee769f9877d17b16b1b46eeaaf019f",
    ),
    "voice_config": (
        "tts/en_US-lessac-medium.onnx.json",
        4885,
        "efe19c417bed055f2d69908248c6ba650fa135bc868b0e6abb3da181dab690a0",
    ),
}


def native_path(path):
    """Avoid a fatal narrow-path espeak failure on Windows; never change system settings."""
    absolute = str(Path(path).resolve())
    if os.name != "nt" or absolute.isascii():
        return absolute
    import ctypes
    function = ctypes.WinDLL("kernel32", use_last_error=True).GetShortPathNameW
    function.argtypes = [ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_uint]
    buffer = ctypes.create_unicode_buffer(32768)
    length = function(absolute, buffer, len(buffer))
    if not length or length >= len(buffer) or not buffer.value.isascii():
        raise ValueError("Native speech component needs an ASCII-compatible local path")
    return buffer.value


def default_models():
    if not getattr(sys, "frozen", False):
        return Path(__file__).resolve().parents[3] / "models"
    manifest = Path(__file__).with_name("external_assets.json")
    if manifest.is_file():
        development = json.loads(manifest.read_text(encoding="utf-8-sig")).get("development_models")
        if isinstance(development,str) and development:
            return local_path(development)
    return Path(os.environ["LOCALAPPDATA"]) / "Autumn/models"


class Assets:
    def __init__(self):
        self.verified = {}

    def get(self, key, root=""):
        relative, size, digest = ARTIFACTS[key]
        directory = local_path(root) if root else default_models()
        path = no_reparse(directory / relative)
        stat = path.stat()
        signature = (str(path), stat.st_size, stat.st_mtime_ns)
        if stat.st_size != size:
            raise ValueError("Model missing or incomplete")
        if self.verified.get(key) != signature:
            with path.open("rb") as stream:
                actual = hashlib.file_digest(stream, "sha256").hexdigest()
            if actual != digest:
                raise ValueError("Model checksum mismatch")
            self.verified[key] = signature
        return path
