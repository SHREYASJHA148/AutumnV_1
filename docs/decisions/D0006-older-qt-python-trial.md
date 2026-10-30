# D0006 — Authorized older Qt/Python experiment
Question: Which bounded experiment follows the three failed standalone launches?
Options: Older pinned Qt/Python; defer standalone and use the source launcher.
Choice: Owner authorized the older combination; test project-local CPython 3.12.10, Qt/PySide6-Essentials 6.8.3, matching shiboken6 6.8.3, PyInstaller 6.22.3 in .venv-qt-compat.
Reason: Measured source and standalone UI launch success without DLL patches; all 11 native/component imports and 10 Piper syntheses pass on 3.12. Focus prerequisite remains unverified, so the strict harness and full Phase 0 gate are not passed. No global Python/registry/PATH or administrator changes.
