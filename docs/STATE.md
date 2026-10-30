# STATE
Phase: 0 — Autumn compatibility spike; Last gate: incomplete; older-stack packaging loading blocker resolved (D0006)
Hardware facts: Windows 11 Home Single Language build 26200; i5-13420H; 15.7 GiB RAM; RTX 5050 Laptop 8151 MiB/driver 621.01; C:59.4 GiB and D:64.4 GiB free.
Runtime facts: Original .venv preserved; .venv-qt-compat uses project-local Python 3.12.10, Qt/shiboken 6.8.3, PyInstaller 6.22.3, hash-locked packages.
Done: Older-stack source and frozen UI launch pass without DLL patches (spaces/é path); 11 imports, volume-worker restart/read-back, hotkey registration and 10 Piper syntheses pass.
Next: Controlled foreground/overlay/hotkey test; model bake-off; owner speech evaluation and remaining Phase 0 checks.
Blockers: Strict compatibility harness fails focus precondition (test target not foreground); loading is fixed. Defender scan unverified; linked review missing; recording/model gates pending.
Stubs: none; no application code started.
Decisions: D0006 older candidate measured; D0003 owner choices/authorization unchanged; no Phase 1 approval.
Dependencies: requirements-qt-compat.lock and requirements-phase0-compat.lock; qt_compat_environment.json licenses; original lock preserved.
Open questions for owner: none; older combination approved; no Phase 1 approval.
Evidence: docs/reports/QT_COMPATIBILITY_ASSESSMENT.md; qt_compat_trial/source/frozen.json; component_probe_py312_qt683.json; piper_tts_py312.json.
