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
        {"name": "Language model", "detail": "Not connected in Phase 1; pinned qwen3:1.7b reserved for Phase 3"},
        {"name": "Recognition", "detail": "Not connected in Phase 1; Phase 0 accuracy findings carried forward"},
        {"name": "Female English voice", "detail": "Lessac medium selected; playback integration in Phase 4"},
        {"name": "Audio devices", "detail": audio},
        {"name": "Microphone permission", "detail": "Not tested here; microphone stays closed"},
        {"name": "Computer actions", "detail": "Simulation only; no Windows action adapter connected"},
        {"name": "Privacy", "detail": "Offline; no audio, transcripts or typed commands persisted"},
        {"name": "Phase 0 carry-forward", "detail": "GPU routing, speech/wake accuracy, cross-window focus and antivirus validation remain open"},
    ]
