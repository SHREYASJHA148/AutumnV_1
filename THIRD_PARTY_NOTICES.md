# Autumn preview dependency and model notices

The current exact distributions and wheel hashes are in `requirements-phase7.lock` (identical dependencies to Phase 6). This personal preview bundles Windows action and speech engines; all language, speech, voice and wake model weights remain separate. The package includes installed license/notice texts under `licenses`, dependency/model provenance in `provenance.json` and the application's source snapshot in `autumn-source.zip`. This is the owner's engineering evaluation package, not a completed public redistribution review.

Phase 3 adds no Python dependency: its bounded loopback client uses the standard library. Ollama is separately installed; qwen3:1.7b remains in Ollama's cache with its pinned digest and existing Phase 0 license inventory. Neither runtime nor model weights are bundled in the executable. Redistribution review remains outstanding.

| Component | Pinned version | License / purpose |
|---|---|---|
| CPython | 3.12.10 | Python Software Foundation; interpreter |
| PySide6-Essentials, shiboken6 | 6.8.3 | LGPL-3.0/GPL-3.0/commercial options; dynamically linked desktop UI |
| Pydantic | 2.14.2 | MIT; contracts/settings |
| pydantic-core | See lock | MIT; validation runtime |
| annotated-types, typing-extensions, typing-inspection | See lock | MIT / PSF-compatible notices in installed distributions; validation typing support |
| PyInstaller | 6.22.3 | GPL-2.0-or-later with bootloader exception; build tool |
| pytest | 9.2.0 | MIT; development test runner |
| Ruff | 0.17.3 | MIT; development linter |
| pywin32 | 312 | PSF; Windows shell, catalog and COM bindings |
| pycaw | 20260927 | MIT; Core Audio |
| comtypes | 1.4.17 | MIT; typed COM interfaces |
| PyWinRT Windows.Media.Control / Foundation / Collections / Storage.Streams | 4!10.0.28000.2705 | MIT; media-session bindings |
| winrt-runtime | 4.0.3 | MIT; PyWinRT runtime |
| Hypothesis | 6.170.14 | MPL-2.0; development property tests |
| Other build/test dependencies | See lock and installed distribution notices | Full license metadata recorded in `docs/reports/phase2_dependencies.json` |

Qt source, relinking/replacement rights, notices and the license text must accompany any public distribution under the chosen license. This inventory is not the completed distribution review. Phase 0 speech/model licenses remain separate.

Implementation references: [Qt native event filters](https://doc.qt.io/qtforpython-6/PySide6/QtCore/QAbstractNativeEventFilter.html), [Windows hotkey registration and reserved F12](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-registerhotkey), [PyInstaller feature notes](https://pyinstaller.org/en/stable/feature-notes.html).

Windows adapter references: [ShellExecuteEx](https://learn.microsoft.com/en-us/windows/win32/api/shellapi/nf-shellapi-shellexecuteexw), [packaged app activation](https://learn.microsoft.com/en-us/windows/win32/api/shobjidl_core/nf-shobjidl_core-iapplicationactivationmanager-activateapplication), [media sessions](https://learn.microsoft.com/en-us/uwp/api/windows.media.control.globalsystemmediatransportcontrolssession).

Planner references: [Ollama chat API](https://docs.ollama.com/api/chat), [structured outputs](https://docs.ollama.com/capabilities/structured-outputs), [thinking controls](https://docs.ollama.com/capabilities/thinking). Application code validates the returned structure independently of the runtime grammar.

Phase 4 speech dependencies are hash-pinned in `requirements-phase4.lock`; installed license metadata is inventoried in `docs/reports/phase4_dependencies.json`. sounddevice 0.5.6 and PortAudio use MIT-compatible notices; NumPy 2.5.4 and SciPy 1.18.1 carry BSD and bundled-library notices; pywhispercpp 1.5.1/whisper.cpp use MIT; webrtcvad-wheels 2.0.14.post1 uses MIT plus the bundled WebRTC BSD notices. Piper 1.8.0 is GPL-3.0-or-later and includes espeak-ng and additional notices; ONNX Runtime 1.31.1 uses MIT. Preserve all installed distribution notices for redistribution review.

Lessac voice weights have their own [2013 Blizzard Challenge Lessac license](https://www.cstr.ed.ac.uk/projects/blizzard/2013/lessac_blizzard2013/license.html), referenced in `models/tts/MODEL_CARD`; engine licenses do not license voice data. The English Whisper weights have separate upstream model terms. Weight hashes/sizes are in `src/autumn/speech/assets.py`; no speech weights are bundled. The executable is a personal development preview, not a completed public distribution.

Speech API references: [sounddevice streams](https://python-sounddevice.readthedocs.io/en/latest/api/streams.html), [pywhispercpp](https://github.com/absadiki/pywhispercpp), [Piper Python API](https://github.com/OHF-Voice/piper1-gpl/blob/main/docs/API_PYTHON.md), [WebRTC VAD wheels](https://github.com/daanzu/py-webrtcvad-wheels). The project packaging hook uses metadata for the installed `webrtcvad-wheels` distribution rather than the legacy `webrtcvad` distribution name.

Phase 6 hash-locks the existing openwakeword 0.6.0 adapter and its dependencies in `requirements-phase6.lock`; the lock/install used the local cache offline. Code is Apache-2.0; the pretrained hey-jarvis wake model is CC-BY-NC-SA-4.0 for personal noncommercial use with attribution/share-alike terms. This is not an interchangeable license with the speech engines. ONNX wake/mel/embedding artifacts are pinned by exact bytes and SHA-256 in `autumn.speech.assets`, with original release URLs in `docs/reports/wake_artifacts.json`. They stay outside the executable. The [openWakeWord project](https://github.com/dscripka/openWakeWord) supplies the detector; no custom wake training is included. The installed distribution inventory is `docs/reports/phase6_dependencies.json`. Complete public distribution/license review remains Phase 7 work.
