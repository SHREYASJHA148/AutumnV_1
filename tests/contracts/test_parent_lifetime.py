"""The data worker must retire when its UI process dies on Windows."""
import ctypes
import json
import os
import subprocess
import sys
import time
from ctypes import wintypes as W
from pathlib import Path


def test_native_parent_crash_retires_data_worker(tmp_path):
    env = {**os.environ, 'PYTHONPATH':str(Path('src').resolve())}
    parent = subprocess.Popen([sys.executable, str(Path('tests/fixtures/parent_crash.py').resolve()), str(tmp_path)], env=env, creationflags=subprocess.CREATE_NO_WINDOW)
    kernel = ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.OpenProcess.argtypes = [W.DWORD,W.BOOL,W.DWORD]
    kernel.OpenProcess.restype = W.HANDLE
    kernel.WaitForSingleObject.argtypes = [W.HANDLE,W.DWORD]
    kernel.CloseHandle.argtypes = [W.HANDLE]
    handle = None
    try:
        deadline = time.monotonic()+12
        while not (tmp_path/'ready.json').exists() and time.monotonic()<deadline:
            assert parent.poll() is None
            time.sleep(.02)
        pid = json.loads((tmp_path/'ready.json').read_text())['pid']
        handle = kernel.OpenProcess(0x100000,False,pid)
        assert handle
        (tmp_path/'crash-now').touch()
        assert parent.wait(timeout=3)==7
        assert kernel.WaitForSingleObject(handle,3000)==0
    finally:
        if handle:
            kernel.CloseHandle(handle)
        if parent.poll() is None:
            (tmp_path/'crash-now').touch()
            parent.wait(timeout=3)
