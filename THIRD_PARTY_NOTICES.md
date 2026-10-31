# Phase 1 dependency inventory

The exact distributions and wheel hashes are in `requirements-phase1.lock`. This personal preview does not bundle model weights, a voice, speech recognition or an action runtime.

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
| Other build/test dependencies | See lock and installed distribution notices | Tooling only; full license metadata recorded in `docs/reports/phase1_dependencies.json` |

Qt source, relinking/replacement rights, notices and the license text must accompany any public distribution under the chosen license. This inventory is not the completed distribution review. Phase 0 speech/model licenses remain separate.

Implementation references: [Qt native event filters](https://doc.qt.io/qtforpython-6/PySide6/QtCore/QAbstractNativeEventFilter.html), [Windows hotkey registration and reserved F12](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-registerhotkey), [PyInstaller feature notes](https://pyinstaller.org/en/stable/feature-notes.html).
