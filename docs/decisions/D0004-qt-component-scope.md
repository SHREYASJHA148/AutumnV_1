# D0004 — Qt dependency scope
Question: Does Phase 0 need the entire Qt Addons/WebEngine distribution?
Options: Full PySide6 metapackage; PySide6-Essentials with the same PySide6 Python namespace.
Choice: Use Essentials for Qt Quick/QML/Widgets/tray experiments; verify actual imports and QML controls before closing D-16.
Reason: Full Addons was still downloading unused browser modules after ten minutes; Essentials avoids dependencies unrelated to current tasks. Cancelled only the project's installer process; no compatibility result is claimed yet.
