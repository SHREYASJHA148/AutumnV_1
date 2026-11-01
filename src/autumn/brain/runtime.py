"""Start the installed local Ollama server; never installs, pulls or starts a shell."""
import os
import socket
import subprocess
import time
from pathlib import Path


def listening():
    try:
        with socket.create_connection(('127.0.0.1',11434),timeout=.25):
            return True
    except OSError:
        return False


def ensure_local_runtime(checkpoint):
    if listening() or not checkpoint():
        return
    candidates = [Path(os.environ['LOCALAPPDATA'])/'Programs/Ollama/ollama.exe',
                  Path(os.environ.get('ProgramFiles',r'C:\Program Files'))/'Ollama/ollama.exe']
    executable = next((path for path in candidates if path.is_file()),None)
    if executable is None:
        return  # Existing planner supplies the usable missing-runtime message.
    if not checkpoint():
        return
    subprocess.Popen([str(executable),'serve'],shell=False,creationflags=subprocess.CREATE_NO_WINDOW,
                     stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,
                     env={**os.environ,'OLLAMA_HOST':'127.0.0.1:11434'})
    deadline=time.monotonic()+5
    while checkpoint() and time.monotonic()<deadline:
        if listening():
            return
        time.sleep(.1)
