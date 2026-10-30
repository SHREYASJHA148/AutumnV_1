# Autumn — Phase 0 closeout

Date: 31 October 2026 (Asia/Calcutta). **Phase 0 is complete by explicit owner acceptance (D0007).** Validation exceptions below remain recorded; this is not an all-tests-passed result. Phase 1 has not started.

## Completed work

| Area | Delivered or measured |
|---|---|
| Product and project setup | Autumn name, English female voice, built-in microphone, screenshot/search folder defaults; canonical PRD/TRD/implementation plan, agent rules, decision records, state handoff and Git history. |
| Hardware inventory | Windows 11 build 26200, i5-13420H, approximately 16 GB RAM, RTX 5050 Laptop with approximately 8 GB VRAM; storage, audio endpoints and installed software inventoried. |
| Compatible Windows stack | Project-local Python 3.12.10, Qt/PySide6-Essentials/shiboken6 6.8.3 and PyInstaller 6.22.3; hash-locked environments and dependency/license manifests. Original environment preserved. |
| Desktop packaging | Source UI and standalone UI launched, including a path with spaces and é; QML and tray supported; no DLL patches required for the older stack. |
| Local female speech | Piper generated ten valid samples and the owner confirmed playback; Windows Zira fallback generated ten samples. |
| Microphone experiments | Owner captured 20 English commands locally. Audio stayed in worker memory and was discarded on fixture closure; no raw audio or transcripts saved. |
| Windows primitives | Volume set/read-back and supervised worker restart passed; temporary keyboard hook down/up, confirmation and Stop hotkey events received; owner-operated fixture overlay focus passed. |
| Filename search | Bounded scan found 40 expected matches among 1,000 disposable files in 0.179 seconds. Windows Search service was stopped, so scan fallback was exercised without changing the service. |
| App/media primitives | Disposable single-instance target handoff passed; WinRT media-session enumeration worked with zero active sessions and no playback changes. |
| Local language model | qwen3:1.7b downloaded, digest recorded, and CPU development evaluation completed: 23/30 correct, median warm request 5.894 seconds, p95 7.445 seconds. No proposed action was dispatched. |
| Wake engine | Three ONNX assets downloaded; inference over ten seconds each of synthetic silence and low-level noise produced no activations at threshold 0.5. |
| Recovery and evidence | Invalid/truncated speech weights were rejected; partial downloads and failure reports retained; temporary diagnostic/download processes stopped at interruption, shared Ollama left running. |

## Validation exceptions carried forward

- The model-only CPU score was below the proposed 85% Phase 0 threshold. The deterministic-plus-model path, candidate comparison, GPU acceleration, peak resources and final brain selection are not validated.
- Larger speech weights and the second language model were not fully downloaded/verified. Do not load partial artifacts.
- Speech scoring originally used normalized exact phrases (6/20), which does not establish command-intent accuracy. The owner reported mostly correct wording with variations. Corrected intent scoring exists but has not completed a fresh comparable owner evaluation on both speech models.
- Cross-process confirmation focus, elevated-window handling, active-capture Stop behavior, packaged Store-app launch, real wake positives/false activations and clean-account installation remain unverified.
- Defender command-line scans returned 0x80508023, including with the current installed platform. No clean antivirus result is claimed and no security settings were changed.
- Full license/distribution review, final disk budget and schedule rebaseline remain open. The included pretrained wake models have noncommercial terms; the short synthetic trial does not establish wake reliability.

These findings are the Phase 0 baseline for subsequent work, not permission to bypass validation or runtime controls. See [interruption details](PHASE_0_INTERRUPTION.md) and [older-stack compatibility evidence](QT_COMPATIBILITY_ASSESSMENT.md). Partial artifacts and prototype fixtures are not a finished Autumn product.
