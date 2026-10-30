# Phase 0 validation interruption

Date: 31 October 2026 (Asia/Calcutta). Validation stopped after the turn was deliberately interrupted. **Phase 0 has not passed.**

Temporary project download clients and the private Ollama diagnostic listener on port 11435 were stopped. The user's shared Ollama app/service on port 11434 was left running. Partial weight files remain for safe recovery and must not be loaded until complete size/SHA checks pass.

## Findings saved before interruption

- Original baseline model GPU evaluation stopped after three timeouts. A CPU-only run completed: 23/30 development cases correct, median warm request 5.894 seconds, p95 7.445 seconds. This is a model-only probe, not the planned combined deterministic/model path. It is below the 85% Phase 0 accuracy threshold; the second candidate was not yet available for comparison.
- Small English recognition weights were truncated twice. Initial expected size 487,614,201 bytes versus 118,509,449 received; no invalid weights were loaded. The second full-range attempt was also incomplete. A third approach using bounded exact byte ranges was making progress when stopped. Final upstream SHA256 remains mandatory.
- Owner completed 20 base.en recordings and confirmed hearing ten Piper samples and the fixture focus test. The first scorer compared literal normalized phrases and matched 6/20. Owner reported the recognition preview was mostly correct with wording differences, so this score must not be represented as command-intent success. The fixture now records both phrase and bounded intent scores, but that version has not had a complete fresh owner run.
- Speech was retained only in worker memory; it was discarded when the owner closed the fixture. No audio or transcript files were saved. A separate local preview observer retained only one late base-model intent label; it cannot reconstruct or score the earlier samples.
- Keyboard hook down/up events, confirmation hotkeys and the independent Stop hotkey were received. Cross-process confirmation focus was not verified; the intended disposable target was not foreground. The hook was removed on fixture exit. Elevated-window behavior and capture cancellation still need explicit tests.
- Bounded scan found 40 expected matches among 1,000 disposable files in 0.179 seconds. Windows Search remains stopped; no service changes were made. Single-instance test target handoff succeeded. Store-app launch was not yet tested.
- WinRT media-session enumeration worked with zero sessions; no titles read or playback modified. Wake inference over ten seconds each of synthetic silence and low-level noise produced no activations at threshold 0.5. Positive owner wake trials and real household false activation were not measured.
- Current Defender service/signatures were detected, but both old and current command-line scanners returned 0x80508023. No clean scan is claimed. No security setting was changed.

## Resume precautions

Read STATE.md first. Preserve the existing result files and failed attempts. Do not treat one successful short CPU reply as GPU validation or the literal phrase score as command accuracy. Verify download integrity and finish the candidate comparison before selecting a brain. Ask for a fresh guided session only after the required speech artifacts are ready, so the owner does not have to wait with recordings in memory. No Phase 1 work is authorized.

The last private GPU diagnostic was started with flash attention disabled, but no inference request or result was collected before interruption. Do not claim that configuration fixes GPU behavior.
