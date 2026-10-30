# Autumn — Older Qt/Python compatibility assessment

Date: 31 October 2026 (Asia/Calcutta)

## Outcome

The standalone QtCore loading blocker is resolved for the tested combination: **CPython 3.12.10, PySide6-Essentials/Qt 6.8.3, shiboken6 6.8.3, PyInstaller 6.22.3**. This is a disposable compatibility build, not the Autumn application. The original Python 3.14/Qt 6.12 environment remains intact.

| Check | Result | Evidence |
|---|---|---|
| Project-local installation | Pass; no global Python, registry or PATH changes | D0006; qt_compat_environment.json |
| Hash-locked dependencies | Pass; minimal packaging and full component environments locked separately | requirements-qt-compat.lock; requirements-phase0-compat.lock |
| Source UI launch | Pass; exit 0, QML loads, tray available | qt_compat_source.json |
| Standalone build | Pass | qt_compat_trial.json; total source/build/launch experiment 157.09 seconds |
| Standalone UI launch | Pass; exit 0, Python 3.12.10, Qt 6.8.3, frozen=true | qt_compat_frozen.json |
| Spaces and non-ASCII path | Pass; executable launched from dist/qt compatibility é/AutumnQtCompat | qt_compat_trial.json |
| Manual DLL patches | None | qt_compat_trial.json |
| Native/audio component imports | All 11 passed on the full Python 3.12 environment | component_probe_py312_qt683.json |
| Volume worker | Two read-back trials and fresh-worker restart passed | component_probe_py312_qt683.json |
| Hotkey registration | Temporary chord registered and unregistered | Delivery and elevated-window behavior remain unverified |
| Female local speech synthesis | Piper generated 10 valid WAV files on Python 3.12 | piper_tts_py312.json; playback and voice quality unverified |
| Overlay focus prerequisite | Not met in source or packaged trial | fixture_has_foreground=false in both reports |
| Focus-preserving overlay | Unverified for the intended test target | Foreground remained unchanged, but belonged to another window; no pass claimed |
| Antivirus | See defender_qt_compat.json; do not infer a clean scan from build success | Separate scan of this new artifact attempted without remediation |

## Why the experiment reports failure despite a working executable

The strict harness verifies more than library loading. It returned nonzero because the disposable editable test window did not gain foreground focus, even though the source, build, and packaged launch exit codes were all zero. The overlay did not steal foreground focus, but that alone does not demonstrate the intended target-window scenario. The harness and its focus requirements have not been weakened or marked passed.

A controlled focus test with an explicitly focused disposable target is still required. Do not diagnose the focus result as proof of a Qt bug or claim the full Phase 0 gate passed.

## Recommendation and remaining work

Use this older stack as the **candidate** for the remaining Phase 0 experiments. Retain the previous environment and failed-build evidence until a final stack is selected. Do not begin Phase 1 before the complete Phase 0 report and owner approval.

Remaining Phase 0 work includes model bake-off and CPU profile, recognition on the owner's speech, actual playback, hold-to-talk and confirmation-hotkey delivery, an appropriately focused overlay test, indexed search and app launch checks, wake-model evaluation, license review, disk/resource measurement, and the final feasibility decision. Earlier evidence from the 3.14 environment is not automatically transferred to changed native dependencies.

## Reproduction

Install the exact project-local Python listed in D0006; create .venv-qt-compat. Install requirements-qt-compat.lock with hash verification for the minimal UI experiment. Run tools/test_qt_compat.ps1. It retains strict foreground assertions and may report a focus failure when Windows does not grant foreground activation.

requirements-phase0-compat.lock additionally includes the component-probe dependencies. Component and TTS probes support separate report filenames through AUTUMN_COMPONENT_REPORT and AUTUMN_TTS_REPORT so the earlier results are preserved.

Upstream context: [Qt 6.8 release notes](https://doc.qt.io/qtforpython-6.8/release_notes/pyside6_release_notes.html), [PyInstaller Windows requirements](https://pyinstaller.org/en/stable/requirements.html). These sources describe supported tooling; the table above reports this laptop's measurements.
