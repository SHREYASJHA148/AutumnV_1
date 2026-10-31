# Pending owner validation — Phase 4

The owner explicitly deferred this session's microphone test. Do not start recording or playback automatically. Synthetic development audio is not evidence for NFR-03, the GPU latency gate, intelligibility on the built-in speakers, or a physically disconnected network.

When the owner resumes testing:

1. Freeze the build, speech/brain digests, enabled capabilities and disposable target catalog before collecting results. Never tune from Phase 3 RC1 or treat this speech run as a rerun of that dataset.
2. In Voice setup, select the built-in input/output, check speech files and local brain, and explicitly press the four-second microphone test and playback controls. Check the preview against the spoken words and confirm the female voice is intelligible. Tests do not dispatch actions.
3. Prepare 100 varied supported English requests in the owner's own wording, covering reviewed disposable apps/folders, numbers, media, screenshots and filename search. Keep any private reference wording separate from logs and reports; no raw audio files are needed. Use only disposable targets and project test folders.
4. For each command, the owner holds/releases the talk control, checks the transient transcript, and observes the result. Tally recognition correctness, routing correctness given the recognized text, and verified end-to-end success separately. Wording differences count as recognition success when intent and arguments match. Keep only anonymous case numbers, outcome categories and timing in the public report.
5. Record endpoint/release-to-action-start timings separately for deterministic and model-routed commands, plus action completion and first spoken response. Report CPU results as CPU; NFR-04 still requires the specified GPU profile. Do not relabel recognition-only synthetic timings as end-to-end latency.
6. Exercise Stop and microphone-off during recording, recognition and playback; issue a typed help request after each. Check no stale action follows cancellation. Switch the default audio endpoint during capture/playback, explicitly refresh, then retest. Bluetooth remains unavailable until a headset is supplied.
7. For NFR-13, the owner can disconnect the network using their own controls and run supported local tasks against disposable targets with all assets already present. Website opening is excluded. Restore connectivity afterward. The requirement also needs a ten-minute network-activity capture showing only loopback except explicit website opens/setup downloads; collect metadata without private request content. Neither trial has been completed by the agent.
8. Report all 100 outcomes, exclusions, device/profile facts, p50/p95 latency, failures and human playback observations. NFR-03 needs at least 90% command success across the full 100 utterances. Phase 3 accuracy failures and all other P0 exceptions remain independent blockers to declaring the personal MVP.

The current UI keeps recognized words only in memory, supports editing and resubmitting as a new typed request, and has no automatic audio-save mode. Stop or microphone-off clears retained test audio. A fresh restart begins with voice disabled.
