# Phase 1 checkpoint — 31 October 2026
Status: PASSED for the foundation/simulation scope; Phase 2 requires owner approval.
| Check | Result and evidence |
|---|---|
| Settings, states, generation cancellation, privacy, migration rollback, worker crash/hang recovery | PASS — 151 tests, 10.44 s; lint clean; `phase1_gate.json` |
| QML interface, diagnostics, bounded queues, history retention/clear, safe startup | PASS — source and standalone smoke checks; `phase1_source.json`, `phase1_frozen.json` |
| NFR-05 input / Stop acknowledgement to rendered frame, 40 samples each | PASS — standalone p95 31 / 16 ms (target ≤200 ms), with active worker and overflow/rapid-cancellation load |
| Shortcut conflicts, native delivery, single-instance focus, shutdown | PASS — native integration tests; separate disposable target had focus before second launch; owned workers closed |
| Standalone build and launch from spaces/non-ASCII path | PASS — `dist/Autumn preview é/Autumn/Autumn.exe`; build 152.042 s; hashes and dependency inventory in JSON reports |
Limits: no live microphone, model inference or real computer actions yet; no actual lock/sleep, elevated-window, Narrator or clean-account claim. Phase 0 GPU/speech/wake/focus/Defender exceptions remain in `PHASE_0_CLOSEOUT.md`; two initial harness AttributeErrors are preserved separately.
