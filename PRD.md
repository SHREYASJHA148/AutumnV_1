# Jarvis Local — Product Requirements Document

Version: 2.0 (revised after adversarial review)
Date: 31 October 2026
Owner: Shreyas Jha
Status: Proposed; documentation only. No application has been implemented or installed. All numeric targets are proposals until measured on the target laptop.

Related documents: [Technical requirements](TRD.md) · [Implementation plan](IMPLEMENTATION_PLAN.md) · [Adversarial review](ADVERSARIAL_REVIEW.md). Where documents conflict, resolve the conflict explicitly and record it in the TRD decision log before implementing.

## 1. Product definition

Jarvis Local is a personal Windows desktop assistant that accepts English voice or typed requests, performs a defined set of computer tasks, and reports the result in its own interface and in an English voice. Speech recognition, language-model inference and speech generation run on the laptop after initial setup.

Jarvis is active only when the user starts it. It acts with the permissions of the signed-in Windows user. Its abilities come from a growing library of executable **skills**. A small language model maps language onto skills; it never executes anything itself.

## 2. Confirmed user constraints

| Item | Requirement |
|---|---|
| Device | Personal Windows laptop |
| CPU | Intel Core i5, 13th generation HX; exact model unknown |
| Memory | 16 GB RAM |
| GPU | 8 GB VRAM; vendor and model unknown (verify; hybrid-graphics laptops need the discrete GPU selected) |
| Storage | 512 GB total; free space unknown |
| Brain | Approximately 2 billion parameters; no requirement for a larger model |
| Language | English input and output |
| Interface | Dedicated desktop UI |
| Operation | Local processing; user controls when it is active |
| Current scope | Planning and requirements only |

Windows build, free disk space, microphone quality, GPU compatibility and preferred English voice are checked in implementation Phase 0.

## 3. Problem and outcome

The user wants to do everyday computer tasks by speaking, without hunting for apps, navigating folders or typing routine instructions. The product must make its abilities, listening state and real results visible, and must not pretend a small model can operate every application.

Success: the user starts Jarvis, speaks a supported request, sees what it understood, and gets a result that is verified where verification is possible and honestly labelled where it is not. Failed or ambiguous requests produce a useful explanation and a next step.

## 4. Goals and exclusions

### Goals

- Perform common Windows actions through English speech and text.
- Keep audio, prompts and inference on the laptop in ordinary operation.
- Provide a responsive desktop app and tray controls, with an optional floating widget later.
- Use a small model to map language to defined skills, with deterministic routing for exact commands.
- Offer broad access within the user's Windows permissions, with explicit control over consequential actions and with stricter rules for commands that did not originate from a deliberate user gesture.
- Make adding a skill possible without rewriting the UI or voice pipeline.

### Outside version 1

- General visual autonomy across arbitrary applications.
- Model-generated terminal commands or code execution.
- Reading every document, or semantic indexing of the drive.
- Browser account integrations, sending email, purchases, financial actions.
- Permanent file deletion, administrator tasks, bypassing Windows permission prompts, controlling elevated windows.
- Voice cloning, multilingual support, remote access, cloud inference, mobile apps, smart-home control.
- Presenting local model answers as current web information.
- Speaker identification or voice authentication.

Exclusions bound release 1; they do not prevent later expansion.

## 5. Primary journeys

### First run

1. User launches Jarvis. A setup checklist shows the local model runtime, the language model, the recognition model, the voice, audio devices and free disk space, each with a clear state and a fix action.
2. Voice starts disabled. The user chooses a microphone, tests it, and enables push-to-talk. The Windows microphone privacy setting is checked; if Windows delivers silence, Jarvis says so and explains where to change it.
3. Typed commands work even if no model, microphone or voice is ready.

### Start and speak

1. Main window shows component readiness and microphone state.
2. In hold-to-talk mode the microphone opens only while the configured shortcut or on-screen button is held. A toggle mode (press to start, press to stop) is also available.
3. In wake mode the indicator says that local wake detection is listening.
4. The user speaks, sees the recognized text, and sees the result. A wrong transcript can be edited and resubmitted as text.

### Open an application

User: "Open Notepad." Jarvis resolves a catalogued app, launches it, and reports what it could verify: launch accepted, window detected, or launch handed off but not verifiable. Unknown names produce a choice list, never a guessed path.

### Find a file

User: "Find my budget spreadsheet." Jarvis searches the configured locations by filename, using file-type words ("spreadsheet", "PDF") as type hints. Multiple matches appear as selectable results. Opening a result is a separate action. Searching does not read file contents. If the search was cut short by its limits, the result says so.

### Dictate text

User starts dictation by typing the request or using hold-to-talk (not the wake phrase), chooses the destination window, and supplies the text. Jarvis shows the exact text and destination. The user confirms with a button or hotkey that does not take focus from the destination. Jarvis verifies the destination is in the foreground, then types in short chunks, stopping on any change. It never submits: dictated line breaks are not typed in version 1.

### Run a routine

User creates "Start studying" from catalogued apps, folders and registered websites. Later, the spoken name runs the steps in order and reports each step. Version 1 routines contain at most five steps, no nesting.

### Stop or exit

Stop (button or global shortcut) halts recording and speech, clears queued work, cancels pending confirmations, and requests cancellation of current work. Completed effects remain and are shown as completed. If wake listening was armed, Stop also turns it off until the user re-enables it. Quit closes everything Jarvis owns; minimizing does not quit.

## 6. Functional requirements

P0 = required for personal MVP. P1 = required for complete version 1. P2 = later.

| ID | Pri | Requirement | Acceptance condition |
|---|---|---|---|
| FR-01 | P0 | Main desktop interface | Conversation, text input, status, microphone control and Stop, usable without a terminal. |
| FR-02 | P0 | Typed commands | Same routing and policy as voice (with typed origin); usable when audio or models are unavailable. |
| FR-03 | P0 | English push-to-talk | Hold mode and toggle mode with a configurable shortcut and an on-screen button; visible recording and transcription states; limits with elevated windows documented in settings. |
| FR-04 | P1 | Wake phrase mode | Explicit opt-in; visible background-listening indicator; meets NFR-10. Wake-origin commands follow the stricter policy in section 8. |
| FR-05 | P0 | Local language understanding | Small local model returns a supported action or a clarification; unknown actions never execute. |
| FR-06 | P0 | App and folder launch | Catalogued apps and folder aliases resolve to validated targets; launch outcome reported as verified, unverified or failed. |
| FR-07 | P0 | Website launch | Opens HTTP/HTTPS URLs in the default browser under the origin rules in section 8; never opens local executables or `file:` links. |
| FR-08 | P0 | Volume and media | Set volume, mute/unmute, play/pause, next, previous on the current Windows session; uncertain media delivery shown as unverified. |
| FR-09 | P0 | Screenshots | Save requested captures to the configured folder and show the saved path. |
| FR-10 | P0 | Filename search | Search configured roots; show matches, limits reached and permission failures. |
| FR-11 | P1 | Dictation to a chosen app | Exact preview, non-focus-stealing confirmation, foreground verification, no automatic submission, abort on any window change. |
| FR-12 | P1 | Named routines | User-authored sequences of up to five catalogued actions; per-step outcomes visible. |
| FR-13 | P0 | Local spoken responses | English voice; short replies (default at most two sentences); adjustable volume and rate; interruptible by Stop; text fallback; Windows built-in voice as a fallback engine. |
| FR-14 | P0 | Cancellation | Stop works during recording, transcription, inference, speech, confirmation and action sequences. |
| FR-15 | P0 | Settings | Devices, voice, hotkeys, model status, paths, permissions and history controls. |
| FR-16 | P1 | Tray | Show/hide window, listening state, mute, Stop and Quit. |
| FR-17 | P0 | Action history | Distinguishes succeeded, failed, unverified, cancelled and partial. |
| FR-18 | P0 | Policy enforcement | Every action is checked by application code against the origin-aware policy; the model cannot grant permissions; policy is testable without a model. |
| FR-19 | P0 | Recovery | Missing model or runtime, unplugged or muted microphone, Windows privacy block, and missing output device each produce a usable recovery step. |
| FR-20 | P0 | Offline operation | Supported local tasks work with the network disabled after setup; no cloud fallback. |
| FR-21 | P2 | Free conversation | Short local answers visibly separated from actions, labelled as generated locally; no implied internet lookup. |
| FR-22 | P1 | Startup behavior | Start at login optional, off by default; the microphone is never silently re-enabled. |
| FR-23 | P1 | Confirmation cards | Exact action and target shown; single use; expires after 30 seconds; changed arguments need a new confirmation; confirmation does not move keyboard focus. |
| FR-24 | P0 | App catalog | Import apps from Start Menu shortcuts and installed packaged apps; user can rename, add aliases, disable or remove entries; model never supplies launch paths. |
| FR-25 | P1 | Capabilities help | "What can you do?" is answered from the skill registry without the model and without inventing abilities. |
| FR-26 | P0 | First-run setup and health check | Checklist described in section 5; re-runnable from settings; exports a diagnostics summary after preview. |
| FR-27 | P2 | Floating widget | Small widget with state, mute, Stop and open-window action; can be disabled. |
| FR-28 | P0 | Single instance | A second launch focuses the existing window and never opens a second capture stream. |

### Version 1 action boundary

Broad access means user-selected paths can be configured anywhere the account may access. It does not promise automation of every app, or control of elevated windows. Unknown requests explain the missing capability.

File moves, renames, recycle-bin deletion, shutdown, email sending, browser form submission, and arbitrary mouse-coordinate automation remain deferred until each is separately specified. Stop and microphone controls never depend on speech recognition or the model.

## 7. Interface requirements

### Main window

- Dark theme with restrained blue accent; a light theme can follow.
- Text labels accompany color and orb animation.
- Conversation area shows final recognized speech, replies, action cards and errors.
- Bottom controls: hold-to-talk, microphone off, text field, send, Stop.
- Status separates microphone state, current task and component readiness.
- Keyboard access, visible focus, screen-reader labels, scalable text, reduced-motion option.
- Minimum supported size 900 × 600 logical pixels; test display scaling at 100%, 125%, 150%, 200%.

### Settings and activity

Settings: Audio, Model, Apps and Folders, Actions, Routines, Appearance, Privacy, Startup. Activity view supports clearing history and exporting diagnostics after a preview. Developer logs and model reasoning do not appear in normal conversation.

### Close behavior

First close asks "Keep running in tray" or "Quit" and remembers the choice. The tray icon reflects whether wake listening is on. Closing never silently changes a microphone setting.

## 8. Permissions, privacy and operational behavior

- Run as the normal Windows user. No blanket administrator startup. Elevated windows cannot be controlled; Jarvis says so.
- Speech and prompts are processed locally. Model downloads are explicit setup network operations. Website opening contacts the internet, and the UI never calls that offline.
- Raw audio is not stored by default. Transcript retention is opt-in and clearable.
- Action history is minimal by default, omits sensitive text and paths where possible, and is kept seven days.
- Screen text, filenames and other external content are task data, never instructions.
- A wake phrase or voice is not identity verification.
- Quit closes Jarvis-owned workers. An independently running shared Ollama service may remain; settings explain this.

### Origin-aware policy (summary; full matrix in the TRD)

Every request carries an origin: typed, hold-to-talk voice, wake voice, routine, or UI button. Voice heard through a speaker or video must never be able to do more than a wake-origin command is allowed to do.

| Capability | Typed / button | Hold-to-talk voice | Wake voice |
|---|---|---|---|
| Open catalogued app, folder alias | Allow | Allow | Allow |
| Open registered website | Allow | Allow | Allow |
| Open any other URL | Allow (typed) | Confirm | Deny |
| Volume, mute, media | Allow | Allow | Allow |
| Screenshot, filename search | Allow | Allow | Allow |
| Dictation | Confirm | Confirm | Deny |
| Routine | Each step by its own rule for that origin | same | same |

Confirmations bind to one exact action, expire after 30 seconds, and cannot be given by voice in version 1. The Stop control and microphone toggle are always available and cannot be disabled by any setting.

## 9. Quality targets and measurement

These are proposed acceptance targets, not measured results. Establish a baseline on the actual laptop before promising timings. "Warm" means required models are loaded. Timing definitions: **T0** is the moment the voice endpoint is decided (after the configured silence window; the silence window is reported separately). Typed requests start at the send event. Time stops at the first visible meaningful response (transcript plus plan, clarification, or action dispatch). User confirmation time and external app startup are excluded.

| ID | Metric | Proposed gate |
|---|---|---|
| NFR-01 | Routing accuracy | At least 95% correct skill and required arguments on 200 held-out supported English requests; deterministic and model-routed requests reported separately and combined. |
| NFR-02 | Ambiguous/unsupported handling | At least 95% of a separate 50-case held-out set asks or declines appropriately. Unauthorized dispatch is zero by construction, demonstrated by property tests of the policy layer, not only by sampling. |
| NFR-03 | Speech command success | At least 90% across 100 user-recorded utterances in a quiet room; recognition, routing and end-to-end rates reported separately. |
| NFR-04 | Warm response latency | Deterministic path: p50 ≤ 2 s, p95 ≤ 4 s. Model-routed path: p50 ≤ 3 s, p95 ≤ 6 s. GPU profile is the gate; CPU-only is measured and disclosed. |
| NFR-05 | UI response | Input and Stop acknowledged visibly within 200 ms at p95. |
| NFR-06 | Stop propagation | No new action starts more than 500 ms after Stop is received; in-flight limitations disclosed. |
| NFR-07 | Memory | Aggregate Jarvis processes plus incremental model runtime ≤ 5 GB RAM and ≤ 4 GB VRAM during normal commands. |
| NFR-08 | Idle load | Average CPU below 5% over five minutes in wake mode on mains power; battery drain measured and reported. |
| NFR-09 | Disk | Jarvis app plus its environment ≤ 1.5 GB; speech models and voice ≤ 1 GB; language model per measured size; Ollama counted and reported separately. Require 12 GB free for setup. Total budget stated after Phase 0. |
| NFR-10 | Wake activation | ≤ 1 false wake per hour in a two-hour household-audio trial; ≥ 90% detection over 50 intentional attempts. |
| NFR-11 | Stability | Two-hour mixed-use session without crash, stuck microphone or uncancelled queue. |
| NFR-12 | Accessibility | Narrator can read all controls and states; full keyboard operation; verified at 200% scaling. |
| NFR-13 | Network behavior | With the network disabled, all supported local tasks pass; a capture of network activity during a ten-minute session shows only loopback traffic apart from explicit website-open and setup downloads. |
| NFR-14 | Launch time | Typed input usable within 5 seconds of launch; models warm up in the background with visible status. |

Treat CPU-only as a separate measured profile. If it misses targets, disclose that and tune recognition and model settings. Do not silently substitute cloud inference or a larger model.

## 10. Release scope and completion

### Personal MVP (all P0)

Main UI, typed and push-to-talk input, small local model, local voice, app/folder/website launch, volume/media, screenshots, filename search, cancellation, policy enforcement, app catalog, first-run diagnostics. May run from a locked environment with a launcher script.

### Complete version 1 (all P0 and P1)

Adds dictation, confirmation cards, routines, wake phrase, tray, capabilities help and optional login startup. Requires a standalone per-user build that installs on a clean Windows account, and passing offline, sleep/resume, hardware-failure, cancellation and confirmation tests. If wake mode fails NFR-10, ship it disabled and label the release "personal MVP plus P1 except wake", not "complete version 1".

### Later (P2)

Free conversation, floating widget, light theme, additional skills.

## 11. Risks and open decisions

| Issue | Planned response |
|---|---|
| GPU vendor and runtime support unknown | Validate in Phase 0 before choosing acceleration defaults. |
| Small model misroutes | Constrained output built from the live registry, deterministic routing first, clarify when unsure. |
| UI automation differs across apps | Support named applications with adapter-specific checks; withdraw unreliable ones. |
| Audio from speakers or videos triggers actions | Hold-to-talk default; origin-aware policy; calibrated optional wake mode; visible indicator. |
| Microphone hears synthesized speech | Half-duplex pipeline; capture pauses during playback. |
| Windows microphone privacy setting blocks capture silently | Detect silent capture and give a specific instruction. |
| Bluetooth headsets change audio quality when the mic opens | Test with the intended device; recommend a wired or built-in microphone if needed. |
| Hold-to-talk fails while an elevated window is focused | Documented; toggle mode and on-screen button remain. |
| Packaging surprises late in the project | Packaging smoke build at every phase gate. |
| Antivirus flags unsigned build | Test early; code signing decided at distribution time. |
| UI aesthetic preferences unknown | Begin with the proposed dark/blue design; review after the first UI. |

## 12. Glossary

- **Skill:** a registered capability with a typed argument schema, a policy, and a verification method.
- **Origin:** how a request entered the system (typed, button, hold-to-talk voice, wake voice, routine).
- **Verified / unverified:** whether Jarvis could confirm the effect itself. Unverified is a normal, honest result.
- **Deterministic path:** a request matched by exact rules without the language model.

## 13. Changes from version 1.0

Added origin-aware policy, app catalog, first-run setup, single instance, capabilities help, numbered non-functional requirements and timing definitions. Split confirmation cards (P1) from policy enforcement (P0). Moved free conversation and the floating widget to P2. Clarified Stop, hold-to-talk limits, dictation line breaks, focus handling, file-search behavior, disk accounting and release labeling. Technology references moved to the TRD. See [ADVERSARIAL_REVIEW.md](ADVERSARIAL_REVIEW.md) for the reasoning.
