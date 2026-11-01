# Autumn 0.7.1 — owner launch and opening extension
- Implemented/configured D0021: automatic pinned local-brain startup, broad installed-app/common-folder/explicit local-path opening, native icon/launcher and addressed hands-free listening while minimized.
- Clickable shortcut: C:\adu\Autumn.lnk; saved personal preferences enabled; original settings backed up; login startup was not enabled; no real microphone opened during configuration or tests.
- Software: 442 unique passing tests (438 full suite plus 4 additional cases); bytecode/UI match current source across 70 bundled modules; native shortcut metadata/ownership tests pass.
- Real local-brain/catalog startup check passed with 154 enabled apps/eight folders, tray icon and simulated capture preserved after minimizing; hardware/false-activation acceptance is pending.
- Standalone visible UI passed at 16 ms p95 input/Stop; installed normal/scale-2 UI and isolated install/removal/data preservation passed. One hidden-window timing failure is retained separately.
- Initial brain startup was unavailable; subsequent real checks passed. Startup-only warm-up budget is now 40 seconds; ordinary command planning retains 15 seconds. A fresh cold-server repeat is not claimed.
- Engineering preview only: prior accuracy failures (81%/80%) and owner audio, GPU, offline trace, clean account/registry, two-hour stability, Narrator/power checks remain unresolved. No passing version-1 release claim.
- Evidence: personal_launch.json and its listed XML/JSON reports; instructions: ../PERSONAL_LAUNCH.md. Questions: none.
