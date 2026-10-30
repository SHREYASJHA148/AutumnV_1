# D0005 — Packaging feasibility route
Question: How can the minimal Qt experiment be packaged without installing a global compiler toolchain?
Options: Add Nuitka/compiler prerequisites for pyside6-deploy; evaluate PyInstaller as the documented alternative.
Choice: Evaluate project-local PyInstaller; pyside6-deploy --dry-run --no-install stopped on missing Nuitka and warned about missing dumpbin. Standalone result remains unverified until built and launched.
Reason: Tests a binary-wheel packager before spending more time downloading a compiler; PyInstaller is GPL-2.0-or-later with a bootloader distribution exception, to be recorded in the inventory.
