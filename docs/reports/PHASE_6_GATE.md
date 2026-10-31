# Phase 6 checkpoint — 31 October 2026
Status: implementation complete; acceptance NOT PASSED; wake remains off/unvalidated; no complete-version-1 declaration or Phase 7 start.
| Check | Result / evidence |
|---|---|
| FR-04 / FR-14 / FR-18 | Implemented: pinned local ONNX wake, explicit calibration/arming, device/model/threshold-bound 50-trial/two-hour/CPU gate, restricted origin, cooldown/endpointing, bounded memory, close-before-playback and Stop/off/session/power/Quit disarm. |
| Desktop / FR-22 | Implemented: stateful tray and Quit, remembered first-close choice, opt-in own-value HKCU startup (never written by tests; microphone stays off), reduced motion, labelled controls and scrollable responsive pages. |
| Software / build | PASS: 391-case full suite plus 2 new regression cases (393 unique); phase6_tests.xml / phase6_regressions.xml; lint, clean 0.6.0 standalone, source/standalone UI and Qt scale-2 layout pass. The oversized-panel failure and width fix are retained in phase6_scale2_before_width_fix.json. |
| Synthetic local pipelines | PASS: real source/standalone ONNX reject 10 s silence and 10 s noise; standalone TTS→PCM→STT processes 10 public examples (9 normalized exact matches). No real microphone, speakers, owner recordings or action dispatch in these probes. |
| NFR-08 / NFR-10 / NFR-12 | UNVERIFIED: actual five-minute mains wake CPU/battery drain, 50 owner wakes/two household-audio hours with speaker media, Narrator, actual Windows 200% and physical sleep/Modern Standby. Synthetic/Qt layout tests do not satisfy these gates; calibration remains absent and arming blocked. |
| Earlier gates / next | Phase 5 native foreground/delivery/overlay-focus trial, Phase 4 owner/GPU/network/hardware tests and Phase 3 accuracy failures remain open. See phase6_gate.json and ../validation/PHASE_5_6_OWNER_TEST.md. Stop at this checkpoint. |
