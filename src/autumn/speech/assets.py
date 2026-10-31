"""Never load unverified/partial speech artifacts and never download on import."""

import hashlib
import json
import os
import sys
from pathlib import Path

from autumn.actions.catalog import local_path, no_reparse

ARTIFACTS = {
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
        return Path(json.loads(manifest.read_text(encoding="utf-8-sig"))["development_models"])
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
