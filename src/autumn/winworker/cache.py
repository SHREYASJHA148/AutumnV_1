"""Keep generated COM bindings inside Autumn's own runtime directory."""
import sys
import types
from pathlib import Path


def configure(root: Path) -> None:
    com_cache = root / "tmp/comtypes"
    win_cache = root / "tmp/win32com"
    com_cache.mkdir(parents=True, exist_ok=True)
    win_cache.mkdir(parents=True, exist_ok=True)
    import comtypes
    if "comtypes.client" not in sys.modules:
        generated = types.ModuleType("comtypes.gen")
        generated.__path__ = [str(com_cache)]
        comtypes.gen = generated
        sys.modules["comtypes.gen"] = generated
    import comtypes.client
    comtypes.client.gen_dir = str(com_cache)
    import win32com
    win32com.__gen_path__ = str(win_cache)
    win32com.gen_py.__path__ = [str(win_cache)]
