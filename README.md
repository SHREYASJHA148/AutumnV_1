# Autumn

A local Windows desktop assistant. Phase 3 adds flexible English text planning with the pinned local `qwen3:1.7b` model, alongside the reviewed app catalog, volume/media controls, screenshots and filename search. Live voice arrives in Phase 4.

Use `dist/Autumn preview é/Autumn/Autumn.exe` after building. Closing its window quits Autumn and its worker. A second launch brings the existing window forward. A shared Ollama service is left running.

For development, run these commands from this folder in PowerShell:

```powershell
.\tools\dev.ps1 run
.\tools\dev.ps1 test
.\tools\dev.ps1 lint
.\tools\dev.ps1 build
```

The measured environment is `.venv-qt-compat` with project-local CPython 3.12.10. Reproduce dependencies with the local `uv` tool and `requirements-phase2.lock` using `--require-hashes`; do not install from the unpinned input file. Older environments and locks are preserved.

Stop is **Ctrl+Alt+Backspace**. **Ctrl+Alt+Space** toggles voice readiness in this preview; it never records. Both controls have on-screen buttons. Change the shortcuts and activity retention in Settings; Diagnostics reports registration conflicts. Every launch starts with the microphone off.

Settings and redacted activity are stored under `%LOCALAPPDATA%\Autumn\`. Activity retains seven days by default and can be cleared. Typed input stays in memory, including transient worker messages, and is never written into history or diagnostics. Corrupt settings are preserved in a recovery copy before safe defaults are created. History clearing is ordinary deletion, not secure erasure. Exported screenshots remain separate user files.

To get started, open **Apps and folders**, import installed apps or choose an executable/shortcut, inspect its target, add aliases and enable it with **Review & save**. Imports skip shell launchers and shortcuts with arguments. Register extra folders and websites explicitly on the same page. Default search roots are Documents and Downloads; Settings controls each capability and the screenshot destination.

Open the separately installed Ollama runtime for flexible commands. **Settings → Check local brain** verifies and warms the existing pinned model. The adapter contacts only literal `127.0.0.1:11434`, ignores proxy/redirect settings, rejects remote models and checks the digest before and after generation. It never downloads or updates a model automatically. The measured default is CPU; GPU acceleration remains unverified. The baseline digest is recorded in Settings/contracts and reports.

Exact commands run before model routing and keep working if Ollama is unavailable. Turn off **Flexible English commands** to use them exclusively. **Save memory** releases the model after each request; otherwise it may stay warm for five minutes. Starting Autumn does not warm the model until a flexible request or explicit check. Quit never stops the separate Ollama runtime.

Model replies pass strict argument, live-registry and origin-policy checks. They never contain executable authority or launch paths. A request has a 15-second planning deadline and at most one repair. Unsupported/unclear input can be declined conservatively; exact names and the supported command forms are the most dependable option. Clarification choices last 30 seconds, preserve the original input authority and disappear on Stop. General conversation, dictation and routines remain unavailable.

Try `what can you do?`, `open <reviewed app or folder name>`, `open https://example.com`, `set volume to 35 percent`, `mute`, `unmute`, `play pause`, `next track`, `previous track`, `take a screenshot`, `screenshot all monitors`, or `find spreadsheet budget in Downloads`. Use exact registered names; fuzzy matches only suggest names. One command at a time; negations, extra instructions and shell text do not execute. The URL example opens your browser only when you explicitly request it.

Search reads filenames inside configured roots, skips reparse points and excluded dependency/system folders, and shows at most 20 matches. The fallback scans for at most 10 seconds / 200,000 entries. Limits and inaccessible entries produce partial results. **Show folder** revalidates a selection, expires after 30 seconds, and opens its containing folder. It does not execute found files. Browser and folder handoff and uncertain media delivery are labelled unverified; actions are never automatically replayed after uncertainty.

For an isolated self-closing UI trial, set `PYTHONPATH` to `src` and run `python -m autumn.main --data-dir <project-test-folder> --phase3-smoke-report <project-report.json>` with the project interpreter. It enters fixed input into Autumn's own controls, searches disposable filenames and validates a local-model capabilities reply. It saves metadata and disposable window screenshots. Older Phase 1/2 trial flags remain available. An explicit isolated data directory is required; the standalone executable accepts the same options.

Canonical specifications and progress live in `docs/`; start with `docs/STATE.md`. Phase 0 exceptions remain in `docs/reports/PHASE_0_CLOSEOUT.md`. Public redistribution requires the complete license and packaging review described in the TRD; this is a personal preview.
