# Phase 0 — Feasibility checkpoint preparation

Date: 31 October 2026 (Asia/Calcutta)  
Status: Incomplete; hardware inspection only. Phase 0 gate has not passed. Evaluated against the current version 2.0 specifications found on disk, not the earlier version 1.0 chat draft.

## Measured inventory

| Item | Observed result | Evidence |
|---|---|---|
| Windows | Windows 11 Home Single Language, 10.0.26200 | Win32_OperatingSystem |
| CPU | Intel Core i5-13420H, 13th generation | Win32_Processor; differs from earlier HX approximation |
| RAM | 15.7 GiB reported | Win32_ComputerSystem |
| Dedicated GPU | NVIDIA GeForce RTX 5050 Laptop GPU, 8151 MiB VRAM | nvidia-smi |
| NVIDIA driver | 621.01 | nvidia-smi; Windows driver 32.0.16.2101 |
| Integrated GPU | Intel UHD Graphics | Win32_VideoController |
| Free space | C: about 59.4 GiB; D: about 64.4 GiB | Get-PSDrive; changes over time |
| Input endpoints | Intel microphone array and Realtek microphone | Present Windows AudioEndpoint devices; audibility not tested |
| Output endpoints | Realtek speakers and headphones | Present Windows AudioEndpoint devices; playback not tested |
| Selected microphone | Built-in microphone array | Explicit owner answer |
| Python | 3.14.6 via explicit installed executable | Executable --version/import probe |
| Python selection | 3.14.6 is installed; compatibility decision D-16 is open | py --list-paths; version 2.0 permits any compatible Python >= 3.11 |
| Default python command | Windows Store alias reports Python not found | python --version |
| Ollama | Client 0.33.2 installed; no running process observed | ollama --version and Get-Process |
| Git | Executable available; project is not yet a Git repository | Get-Command and git rev-parse |
| Windows Search service | Stopped at inspection time; not started by this task | Get-Service WSearch; root coverage and query performance unverified |
| Antivirus | Windows Defender registered | SecurityCenter2 AntivirusProduct; no build scan yet |
| Microphone privacy | User microphone consent value Allow | Registry inspection only; actual desktop-app capture remains untested |

Existing Python module-presence probe: Pydantic and pytest present; PySide6, sounddevice, and onnxruntime absent. This does not establish compatible package versions. Nothing was installed or imported for audio capture.

After the initial inventory, a project-local Git repository was initialized to support the owner's task-commit convention. No global Git settings were changed.

## Component experiment / bake-off table

| Experiment | Candidate | Measurement | Status |
|---|---|---|---|
| Structured routing, same 30 development requests per model | qwen3:1.7b baseline; qwen3.5:2b candidate; optional gemma4:e2b only after size verification/required approval | No requests run; digests, availability, size and licenses unknown | Pending authorization |
| Warm/cold inference and RAM/VRAM | Local Ollama | Not measured | Pending runtime/model readiness |
| CPU fallback | Same approximately 2B candidate | Not measured | Pending runtime/model readiness |
| English recognition, same 20 owner recordings | base.en vs small.en; integration D-03 open | No recordings captured or transcribed | Pending dependency setup and explicit recording session |
| English speech, 10 phrases | Piper plus Windows built-in voice fallback; voice choice pending | No speech generated or played | Pending voice choice and dependency setup |
| Qt window/tray smoke build | PySide6/QML | Not built or launched | Missing project environment and dependency |
| Native Windows adapter experiment | Volume read-back and worker kill/restart | Not run | Pending component spike |
| Wake phrase availability/compatibility | Pretrained hey jarvis, ONNX, license check | Not checked | Pending permitted source/artifact access |
| Hold-to-talk and Stop | Hook vs hotkey, including elevated foreground behavior | Not measured | Pending isolated experiment; no administrator use authorized |
| Non-activating confirmation overlay | Preserve foreground target while receiving confirmation | Not built | Pending Qt environment |
| Filename search backend | Scoped Windows Search query vs bounded scan | Not measured | Pending intended roots and project test fixtures |
| App catalog launch types | Packaged app and single-instance app | Not run | Pending disposable launch experiments |
| Packaging and antivirus | Minimal build in a path with spaces, installed scanner | Not built/scanned | Pending environment; scanner availability to inventory |

No alternate model bake-off has been run. Do not substitute guessed latency, accuracy, compatibility, or memory figures for measurements.

## Gate table

| Phase 0 criterion | Result | Evidence or missing work |
|---|---|---|
| Hardware and runtime inventory | Partial pass | Inventory captured; actual audio and GPU inference not tested |
| Compatible isolated project environment | Not verified | Installed 3.14.6 candidate; full native dependency compatibility untested |
| Small local model works | Not verified | No inference run |
| English recognition works | Not verified | No microphone experiment |
| English synthesis works | Not verified | No engine/voice experiment |
| Minimal QML/tray build launches | Not verified | No build performed |
| One native Windows action works | Not verified | No adapter experiment |
| Dependency/model manifest and licenses | Not verified | Candidate list only; no hashes or pinned artifacts yet |
| All open TRD decisions and schedule rebaseline | Not verified | D-02/03/15–20 remain open; no replacement chosen |
| Version 2.0 early stop thresholds | Not evaluated | Need >=85% development model routing and >=80% owner speech command success before Phase 1 |

## Go/no-go and blockers

GO for completing Phase 0 after pending preferences and permissions are supplied. NO-GO for Phase 1: earlier exit criteria have not been demonstrated.

The owner's standing rules require approval before network access, installs outside the project, and writes outside the project or JarvisLocal app-data directory. Ollama's model cache normally lies elsewhere; a permitted cache location must be established before pulling a model. No runtime connection, model pull, package download, administrator action, or personal-file test has occurred.

Pending owner choices: screenshot/search folders and their access permission, English voice style, and local runtime/download/cache approval. Built-in microphone choice is already confirmed. No need to ask which Windows version or whether Ollama is installed; these were detected.

The version 2.0 specifications link to ADVERSARIAL_REVIEW.md, but that file was not present with the three supplied specifications. Preserve the references and record the missing source; do not invent its contents. Current implementation decisions come from the actual version 2.0 specifications and owner standing rules.

## Next experiments

1. Establish a project-local compatible Python/dependency environment without global installation.
2. Validate local model artifact availability and pin the tested digest, then run bounded development requests and resource probes.
3. Run the recognition, synthesis, disposable action, and QML packaging experiments; save commands, results, versions, and failures.

Stop after Phase 0 with the completed report and owner review. No Phase 1 application work is authorized yet.
