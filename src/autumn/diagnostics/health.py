"""Read-only, offline diagnostics; never opens a microphone or contacts a runtime."""
import ctypes
import os


def snapshot() -> list[dict[str, str]]:
    try:
        inputs = ctypes.WinDLL("winmm").waveInGetNumDevs() if os.name == "nt" else 0
        outputs = ctypes.WinDLL("winmm").waveOutGetNumDevs() if os.name == "nt" else 0
        audio = f"{inputs} input / {outputs} output endpoints reported; no stream open"
    except OSError:
        audio = "Device enumeration unavailable; no stream open"
    return [
        {"name": "Language model", "detail": "Pinned local qwen3:1.7b; use Settings to check runtime availability"},
        {"name": "Recognition", "detail": "Local English small.en/base.en; use Voice setup to verify files and explicitly test the microphone"},
        {"name": "Female English voice", "detail": "Local Lessac medium, with Windows Zira fallback on default speakers; test explicitly in Voice setup"},
        {"name": "Audio devices", "detail": audio},
        {"name": "Microphone permission", "detail": "Not tested here; microphone stays closed"},
        {"name": "Computer actions", "detail": "Typed action engine connected; only enabled skills and reviewed registered targets"},
        {"name": "Privacy", "detail": "Offline; no audio, transcripts or typed commands persisted"},
        {"name": "Phase 0 carry-forward", "detail": "GPU routing, speech/wake accuracy, cross-window focus and antivirus validation remain open"},
    ]
