# Phase 2 dependency inventory

The exact distributions and wheel hashes are in `requirements-phase2.lock`. This personal preview bundles Windows action bindings; model weights, a voice and speech recognition remain separate.

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
