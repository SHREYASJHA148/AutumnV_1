# Jarvis Local — Detailed Implementation Plan

Version: 2.0 (revised after adversarial review)
Date: 31 October 2026
Status: Work breakdown only. No installation, development or benchmarking has started.

Companion documents: [PRD](PRD.md) · [TRD](TRD.md) · [Adversarial review](ADVERSARIAL_REVIEW.md).

## 1. Delivery approach

Build a working vertical slice early: typed command → validated action → visible result. Add local model routing, audio and richer presentation around that proven path. Finish with dictation, routines, wake mode and polish. Keep the model small throughout.

Rules that apply to every phase:

- **Gates, not dates.** A phase is done when its exit gate passes with recorded evidence.
- **Packaging smoke build at every gate** from Phase 1. A phase does not close if the app no longer builds and launches.
- **Skill set freezes at the end of Phase 2.** Held-out datasets are created after the freeze and are not used for tuning.
- **Regression after change.** Any change to model, schema, skill, runtime or audio stack reruns the relevant evaluations.
- **Decision records.** Each Phase 0 open decision (TRD section 2) is closed with a short written record in `docs/decisions/`.

Release tiers: the **personal MVP** contains all P0 requirements. **Complete version 1** adds all P1 requirements. If wake mode fails its gate, ship it disabled and label the release accurately. P2 items (free conversation, floating widget) are not part of version 1.

## 2. Assumptions and setup checks

Confirmed: 16 GB RAM, 8 GB VRAM, 13th-generation i5 HX CPU, 512 GB drive, English voice, dedicated Windows UI, approximately 2B brain.

To establish in Phase 0 on the actual laptop: exact Windows build; GPU vendor, model, driver, and whether the discrete GPU is used on hybrid graphics; free disk space; audio devices and whether the Windows microphone privacy setting allows desktop apps; wanted screenshot, search and app locations; antivirus product in use.

Proposed stack: Python, PySide6/QML, local Ollama, whisper.cpp, Piper with Windows voice fallback, openWakeWord, pywin32 and related Windows APIs, SQLite. Upstream references are in the TRD.

## 3. Phase 0 — Compatibility and feasibility spike

Estimated effort: 3–5 focused days.

Tasks:

1. Record the hardware and software profile from section 2.
2. Pick the Python version: the newest for which every native dependency installs and imports. Create a hash-locked environment.
3. **Model bake-off.** Test `qwen3:1.7b`, `qwen3.5:2b`, and optionally a QAT `gemma4:e2b` on the same 30 development requests with schema-constrained output. Record accuracy, digest, file size, load time, warm latency, peak RAM and VRAM. Verify disabling thinking per model, and that structured output still conforms. Check that any remote or cloud model tag is rejected by the adapter.
4. Measure CPU-only fallback for the leading candidate.
5. **Recognition bake-off.** Transcribe 20 recordings of the owner's speech, including app names, numbers and the chosen microphone, with `base.en` and `small.en`. Test silence and noise clips for invented text. Pick the integration option (TRD D-03) and record the result.
6. Generate and play ten Piper responses; verify install route, voice license and a Windows built-in voice fallback.
7. Prove one Windows adapter in a worker process: set volume with read-back, and kill the worker to confirm clean restart.
8. Prove hold-to-talk: key-down and key-up detection using the planned mechanism; check behavior while an elevated window is focused; confirm Stop works as a plain hotkey; check for hotkey conflicts.
9. Prove focus handling: a non-activating overlay that can receive a hotkey while another app keeps focus.
10. Check Windows Search index availability for the intended roots; time a query. Compare to a bounded scan.
11. Check launching a packaged (Store) app and a single-instance app from a catalog entry.
12. Evaluate the pretrained "hey jarvis" wake model on a short trial; record license terms.
13. Build a minimal QML window with a tray icon, run it from a path containing spaces, and run the planned packager once. Scan the result with the installed antivirus.
14. Record the compatibility matrix, pinned artifacts, download sizes, a disk table (app, environment, speech models, voice, language model, Ollama), and the license inventory.

Deliverables: feasibility report, dependency and model manifest, initial benchmark sheet, closed decision records, and a re-baselined schedule for the remaining phases.

Exit gate: each component works independently on the target laptop, or has a documented replacement. No cloud dependency is accepted as a silent workaround. Go/no-go is written down, with reasons. **Stop criteria:** if no candidate model of the target size class reaches 85% on the development set with the deterministic path in place, or if recognition on the owner's speech is below 80% command success with the best local setting, stop and redesign scope (narrower phrasing, typed-first product) before Phase 1.

## 4. Phase 1 — Foundation and UI skeleton

Estimated effort: 3–4 days. Depends on Phase 0.

Tasks:

1. Repository, package layout, development commands, locked environment, linting and test runner.
2. Typed settings with schema version, atomic save, safe defaults, microphone disabled at start, corrupt-settings recovery.
3. Controller event contracts and separate capture and task state machines (including `PTT_READY`).
4. Single-instance guard.
5. Main QML window: status, conversation, text box, send, microphone control, Stop. Accessible names and roles from the start.
6. Diagnostic status screen for model runtime, recognition, speech output, audio devices and permissions.
7. Bounded worker queues, request IDs, cancellation generations, supervised worker framework, deterministic shutdown.
8. SQLite migrations and action-history storage with retention controls.
9. Global hotkey registration with conflict detection and an on-screen fallback for every hotkey.
10. Packaging smoke build and a skeleton of the test infrastructure (fake adapters, injectable audio source).

Deliverable: launchable app accepting typed input, showing simulated events, stopping and resetting correctly without any model loaded.

Exit gate: no work blocks the UI; state transitions, shutdown, settings recovery and cancellation-generation tests pass; input and Stop acknowledgement meet NFR-05 in a load trial; the smoke build launches.

## 5. Phase 2 — Action engine and deterministic commands

Estimated effort: 6–8 days. Depends on Phase 1.

Tasks:

1. Skill registry, typed argument schemas, and a registry-generated capabilities help.
2. Independent semantic validation and the origin-aware policy matrix, with property tests.
3. **App catalog:** import Start Menu shortcuts and packaged apps; user rename, aliases, disable and remove; descriptor types (executable, shortcut, package identity).
4. App, folder and website launch adapters with best-effort verification and honest `unverified` results; registered websites and the unregistered-URL rules.
5. Volume, mute and media adapters in the Windows worker process; media-session binding chosen in Phase 0.
6. Screenshot saving with DPI-aware capture and artifact cards.
7. Cancellable filename search using the Phase 0 backend, type-word hints, limits, partial results and match selection.
8. Deterministic command grammar with fuzzy alias matching, trailing-word and negation rejection.
9. Serial execution, per-skill deadlines, safe retry rules.
10. Action history view; per-skill enable and disable in settings.
11. **Freeze the skill set and argument definitions.** Start writing the held-out datasets from the frozen definitions (section 13).

Deliverable: a useful typed-command assistant with real computer controls.

Exit gate: representative commands succeed against disposable Windows targets. Unknown apps, invalid URLs, path escapes, access denial, packaged and single-instance launches, cancellation, uncertain media delivery and a hung adapter each produce the specified outcome. Policy property tests pass. No action accepts model-generated shell text. Smoke build launches.

Earliest useful checkpoint: this phase.

## 6. Phase 3 — Small local brain

Estimated effort: 5–7 days. Depends on Phase 2.

Tasks:

1. Loopback-only model adapter with health checks, digest reporting and enforcement, allowlist, `keep_alive` policy, deadlines and cancellation.
2. Planner JSON Schema generated per request from the live registry (enums for app, folder, routine and file-candidate IDs), and Pydantic discriminated unions.
3. Compact prompt with capability descriptions; explicit clarification and unsupported variants. If schema size hurts speed or accuracy, test a two-call design.
4. Deterministic matching stays ahead of model routing; measure how much traffic it covers.
5. Semantic resolution against current registries only.
6. Limits on context, output, plan length, repairs and pending queue.
7. Clarification choices in the UI with expiry and bounded follow-up context.
8. Completion messages rendered from adapter results.
9. Build development and held-out datasets (section 13) and run them, including negation, corrections, ambiguous names, invalid paths and embedded-shell-command attempts.

Deliverable: flexible English text commands routed through the approximately 2B model.

Exit gate: NFR-01, NFR-02 and the model-path part of NFR-04 pass, or the shortfall and its cause are recorded. Record digest, settings, error breakdown and latency. If targets fail, improve the catalog, prompts and rules, ask for missing information, or narrow phrasing. Do not enlarge the model without a product decision.

## 7. Phase 4 — English speech and local voice

Estimated effort: 5–7 days. Depends on Phases 1 and 3.

Tasks:

1. Device enumeration and selection, level meter, test-record and test-play.
2. Bounded capture buffer, resampling, hold-to-talk and toggle modes, on-screen hold button, voice-activity detection, maximum utterance length, device-failure recovery, silent-capture detection with a pointed message.
3. Recognition worker per the Phase 0 decision; display recognized text; reject empty and no-speech captures; allow editing a wrong transcript and resubmitting as text.
4. Speech output with volume and rate controls, short-reply policy, Windows voice fallback and text fallback.
5. Half-duplex suspension during playback and acoustic-tail handling.
6. Stop across capture, transcription, routing and playback; stale results ignored.
7. Temporary audio removed after every outcome and after crashes.
8. Evaluate 100 held-out user-recorded utterances; report recognition, routing and end-to-end separately.
9. Test a Bluetooth headset and a changed default audio device.

Deliverable: voice-driven personal MVP.

Exit gate: NFR-03 and NFR-04 on the GPU profile pass; a network-disconnected command trial passes (NFR-13); text stays usable when microphone or voice is unavailable; smoke build launches. **Personal MVP is declared here** if all P0 acceptance conditions pass, with first-run setup (FR-26) completed.

## 8. Phase 5 — Confirmed dictation and routines

Estimated effort: 3–5 days. Depends on Phase 4.

Tasks:

1. Window picker and editable-control detection for supported applications.
2. Non-activating confirmation overlay and global confirm and cancel hotkeys (FR-23).
3. Confirmation records bound to immutable arguments, target snapshot, request, origin, expiry and single use.
4. Foreground and focus verification before and between chunks; Unicode input; line-break rejection; password and elevated-window refusal; no clipboard paste by default.
5. Dictation tests against the purpose-built target application, including a focus-stealing window.
6. Routine editor from catalogued actions with reorder, delete, validation and preview; deterministic name resolution; at most five steps, no nesting.
7. Serial routine execution with per-step policy for the routine's origin; halt on first failure; summarize completed effects.

Deliverable: reliable dictation to supported apps; user-defined routines.

Exit gate: stale approvals, changed targets, changed text, focus loss, line-break attempts, cancellation, and partial routine failure behave correctly. No duplicate typing after timeouts or worker restarts.

## 9. Phase 6 — Wake phrase and desktop polish

Estimated effort: 4–6 days. Depends on Phase 4; Phase 5 may come before or after.

Tasks:

1. ONNX wake detection with explicit opt-in and calibration; start with the pretrained "hey jarvis" model per Phase 0.
2. Arming, cooldown, command-capture endpointing, playback suppression, lock and sleep handling (classic and Modern Standby).
3. 50 intentional wake trials and a two-hour household-audio false-activation trial; also measure with media playing through speakers.
4. Verify wake-origin restrictions: a wake-started request cannot open an unregistered URL or start dictation.
5. Tray controls and first-close choice; unambiguous Quit.
6. Reduced motion, keyboard navigation, accessible labels, high-DPI layouts; Narrator pass.
7. Optional login startup, default off; microphone stays disabled after launch.
8. Floating widget is P2 and only starts if time remains after gates pass.

Deliverable: complete version 1 interaction if wake and other P1 gates pass.

Exit gate: NFR-08, NFR-10 and NFR-12 pass without unacceptable CPU load; no capture survives microphone-off, lock, sleep or Quit; window and tray show consistent state. If wake fails, keep it disabled and label the release honestly.

## 10. Phase 7 — Packaging, recovery and acceptance

Estimated effort: 4–6 days. Depends on the declared release scope.

Tasks:

1. Freeze dependencies and model checksums or digests; build the standalone app and per-user installer.
2. First-run setup in the packaged app: device checks, local runtime prerequisite, explicit model downloads, license notices, free-space check.
3. Verify downloads; recover from interrupted or corrupt artifacts.
4. Test a clean Windows user without development tools or inherited path assumptions; test Windows Defender behavior.
5. Verify offline operation, no cloud fallback, no unexpected network traffic, and no Jarvis listener beyond loopback (NFR-13).
6. Fault injection: unplugged devices, unavailable runtime, corrupt settings, worker crashes, permission errors, full disk, model timeouts, second instance.
7. Stop tests at every pipeline stage, measuring acknowledgement and dispatch suppression separately.
8. Measure cold and warm timings, peak aggregate resources, idle CPU on mains and battery, and a two-hour stability run (NFR-11).
9. Test display scaling, keyboard-only use, Narrator, paths with spaces and non-ASCII characters, multiple monitors.
10. Write a short user guide, known limitations, troubleshooting guide, and uninstall and data-retention explanation.
11. Complete the traceability checklist and record failures explicitly.

Deliverables: packaged release, acceptance report, user guide, manifest, known-issues list.

Exit gate: all requirements in the declared tier pass. No unresolved issue may allow cancelled or stale plans to execute, confirmations to be reused, or capture to remain active after Quit.

## 11. Proposed repository structure

```text
jarvis-local/
  pyproject.toml
  lockfile                # hash-pinned
  src/jarvis_local/
    main.py
    ui/                   # QML, view models, tray, overlay, widget
    controller/           # State, events, lifecycle, cancellation
    audio/                # Devices, capture, playback, VAD, wake, hotkeys
    speech/               # Recognition and synthesis adapters
    brain/                # Model client, prompts, schema generation
    actions/              # Registry, catalog, executor client, skill adapters
    winworker/            # Windows adapter worker process
    policy/               # Origins, matrix, confirmations, target checks
    storage/              # Settings, database, retention, migrations
    diagnostics/          # Health checks, timing, export filtering
  tests/
    unit/
    property/
    contracts/
    windows_integration/
    fixtures/             # recorded audio, fake adapters, target test app
  evaluation/
    datasets/             # development/ and heldout/ (access-controlled, see §13)
    runners/
    reports/
  packaging/
  docs/
    decisions/
```

The structure is proposed. Do not commit model weights, recordings, personal transcripts, local databases or sensitive diagnostics. Held-out datasets are committed only as hashes until the final evaluation.

## 12. Traceability

One developer can own everything initially; still name an owner and an evidence item for each gate.

| Requirements | Phase | Evidence |
|---|---|---|
| FR-01, FR-02, FR-15, FR-28 | 1–2 | UI walkthrough, settings tests, typed-command trial, second-launch test |
| FR-18, FR-24, FR-25 | 2 | Policy property tests, catalog tests, registry-driven help |
| FR-05 | 3 | Held-out routing evaluation; NFR-01, NFR-02 |
| FR-06 to FR-10 | 2 | Windows adapter integration results |
| FR-03, FR-13, FR-26 | 4 | Voice dataset, playback and first-run checks |
| FR-11, FR-12, FR-23 | 5 | Focus, confirmation, expiry and routine failure tests |
| FR-04, FR-16, FR-22 | 6 | Wake evaluation, tray behavior, login behavior |
| FR-14 | 1–7 | Cancellation and stale-event checks at each stage |
| FR-17 | 1–7 | Outcome and history consistency checks |
| FR-19, FR-20 | 4 and 7 | Fault injection and disconnected run |
| FR-21, FR-27 | later | P2, not in version 1 |
| NFR-01, NFR-02 | 3 | Held-out text evaluation |
| NFR-03, NFR-04 | 4 | Voice dataset and latency report |
| NFR-05, NFR-06 | 1, 7 | Responsiveness and Stop propagation trials |
| NFR-07, NFR-08, NFR-09 | 0, 6, 7 | Resource and disk reports |
| NFR-10 | 6 | Wake trials |
| NFR-11, NFR-13, NFR-14 | 7 | Stability, network capture, launch time |
| NFR-12 | 6–7 | Keyboard and Narrator pass |

## 13. Evaluation protocol

1. Freeze the skill set and arguments at the end of Phase 2 before building held-out data.
2. **Lock-box rule.** Development data (any size) is used for prompt and rule tuning. Held-out data is written once after the freeze, stored as a hash, and not opened for tuning. Look at held-out results once per release candidate. If the held-out set is used for tuning, discard it and write a new one.
3. Make held-out wording varied: write some requests yourself, some from other people or tools, and some from real recorded speech transcripts of your own usage. Do not paraphrase the prompt's own examples.
4. Label expected skill and required arguments, or clarification, or unsupported.
5. Include negation, corrections, ambiguous names, unsupported requests, invalid paths and attempts to embed shell commands.
6. Score routing without execution first, then run end-to-end action trials on disposable targets.
7. Report routing and argument accuracy, deterministic share, failure categories, p50 and p95 latency with the PRD timestamps, CPU, aggregate RAM and GPU memory. With 200 cases, a 95% result has about ±3 points of uncertainty; report intervals.
8. Authorization safety is shown by property tests over the policy layer, not by counting zero failures in a sample.
9. Evaluate recognition and wake separately from routing, with the owner's accent and realistic rooms.
10. Re-run relevant checks after model, schema, skill, runtime or audio changes. Do not widen testing without a change or concern.

The release report states sample sizes, hardware, model digest, cold and warm definitions, noise conditions, and what was excluded.

## 14. Critical path and effort estimate

Critical path: Phase 0 → controller and UI → action engine → local planner → speech integration → acceptance.

| Phase | Estimate (focused days) |
|---|---|
| 0 Spike | 3–5 |
| 1 Foundation | 3–4 |
| 2 Action engine | 6–8 |
| 3 Brain | 5–7 |
| 4 Voice | 5–7 |
| 5 Dictation, routines | 3–5 |
| 6 Wake, polish | 4–6 |
| 7 Packaging, acceptance | 4–6 |
| **Total** | **33–48**, plus 25% contingency |

This is my estimate, not a measurement. It assumes one experienced developer, no custom wake training and no major component replacement. Part-time work stretches the calendar. Re-baseline after Phase 0. Earliest useful checkpoint: end of Phase 2. Personal MVP: end of Phase 4. Complete version 1: end of Phase 7 if all gates pass.

## 15. Risks and fallback decisions

| Risk | Trigger | Response |
|---|---|---|
| GPU acceleration unsupported or discrete GPU not used | Crash, or CPU-speed inference | CPU profile, backend tuning, disclose measured latency. |
| 2B routing misses target | Held-out errors persist | Simplify schemas, strengthen exact routes, clarify more, narrow phrasing. |
| Recognition too slow or inaccurate | Warm targets or NFR-03 missed | Tune endpointing and model size; evaluate another local recognizer. |
| Piper Windows install fails | Spike cannot synthesize | Use the Windows voice or another verified offline voice; keep the adapter interface. |
| Pretrained wake model poor in your room | NFR-10 missed | Keep hold-to-talk; try a different threshold and verification options; estimate custom training separately. |
| Hold-to-talk hook blocked or flagged | Antivirus alert, or no events while elevated | Toggle mode and on-screen button; document; test signing options. |
| UI automation unreliable for an app | Unstable controls | App-specific adapter or withdraw the capability with a visible explanation. |
| Packaging fails on a native dependency | Smoke build fails | Switch packager; keep launcher-based personal release. |
| Disk budget exceeded | Models and runtime above budget | Reduce model size or revise the budget with measured numbers. |
| RAM contention | Peak above budget | Limit concurrency, shorten context, unload owned workers, remeasure. |
| Windows Search index unavailable or incomplete | Phase 0 or user machine | Bounded scan fallback with disclosed limits. |
| Schedule slip | Any phase exceeds its range by 50% | Cut to the personal MVP plus P1 items in priority order: confirmation and dictation, tray, routines, wake. |

## 16. Completion checklist

- [ ] Hardware, Windows build, GPU path, disk, microphone and antivirus facts recorded.
- [ ] Exact dependency versions, model digests and licenses recorded; Phase 0 decisions closed.
- [ ] Supported capabilities and exclusions match PRD and TRD.
- [ ] Typed and English voice journeys succeed locally.
- [ ] Window, tray and overlay represent listening and task state accurately.
- [ ] Origin policy, confirmation binding and Stop behavior pass tests.
- [ ] Wake-origin restrictions verified.
- [ ] Offline operation and network capture verified.
- [ ] Privacy defaults and history cleanup verified.
- [ ] Resource, latency and disk report completed on the actual laptop.
- [ ] Clean-account installation and uninstall checked.
- [ ] User documentation and known limitations delivered.
- [ ] Release tier labeled accurately.

## 17. Next action when implementation is authorized

Begin Phase 0 and validate the components on the actual laptop. The present deliverable is planning documents only; nothing here means installation or development has occurred.

## 18. Changes from version 1.0

Re-baselined estimates; Phase 0 expanded into a bake-off and feasibility spike with stop criteria; packaging smoke builds moved to every gate; added the app catalog, policy matrix, confirmation overlay, supervised Windows worker, Windows Search backend and first-run setup tasks; added the lock-box evaluation rule and interval reporting; traced non-functional requirements; moved free conversation and the floating widget out of version 1. See [ADVERSARIAL_REVIEW.md](ADVERSARIAL_REVIEW.md).
