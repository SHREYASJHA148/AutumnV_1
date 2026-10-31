# Autumn

A local Windows desktop assistant. The Phase 1 preview provides the interface and application foundation. Typed requests produce labelled simulations; computer actions and live voice are not connected yet.

Use `dist/Autumn preview é/Autumn/Autumn.exe` after building. Closing its window quits Autumn and its worker. A second launch brings the existing window forward. A shared Ollama service is left running.

For development, run these commands from this folder in PowerShell:

```powershell
.\tools\dev.ps1 run
.\tools\dev.ps1 test
.\tools\dev.ps1 lint
.\tools\dev.ps1 build
```

The measured environment is `.venv-qt-compat` with project-local CPython 3.12.10. Reproduce the foundation dependencies with the local `uv` tool and `requirements-phase1.lock` using `--require-hashes`; do not use the unpinned input file to install. The older Phase 0 environment and locks are preserved.

Stop is **Ctrl+Alt+Backspace**. **Ctrl+Alt+Space** toggles voice readiness in this preview; it never records. Both controls have on-screen buttons. Change the shortcuts and activity retention in Settings; Diagnostics reports registration conflicts. Every launch starts with the microphone off.

Settings and redacted activity are stored under `%LOCALAPPDATA%\Autumn\`. Activity retains seven days by default and can be cleared. Typed input appears in a bounded in-memory conversation and is discarded on exit; it is never sent to the worker or written into history. Corrupt settings are preserved in a recovery copy before safe defaults are created. History clearing is ordinary deletion, not secure erasure.

For an isolated, self-closing UI check, set `PYTHONPATH` to `src` and run `python -m autumn.main --data-dir <project-test-folder> --smoke-report <project-report.json>` with the project interpreter. This test enters fixed text into Autumn's own controls and saves only metadata and a screenshot of that disposable window. The standalone executable accepts the same options.

Canonical specifications and progress live in `docs/`; start with `docs/STATE.md`. Phase 0 exceptions remain in `docs/reports/PHASE_0_CLOSEOUT.md`. Public redistribution requires the complete license and packaging review described in the TRD; this is a personal preview.
