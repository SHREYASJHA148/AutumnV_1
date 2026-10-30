# Autumn Phase 0 — Feasibility checkpoint

Date: 31 October 2026 (Asia/Calcutta)  
Status: Phase 0 remains incomplete. After owner approval, Python 3.12.10 / Qt 6.8.3 resolved the standalone loading blocker; see [the newer compatibility assessment](QT_COMPATIBILITY_ASSESSMENT.md). Its strict focus prerequisite remains unmet. The earlier failed-build and initial inventory tables below are historical, not the latest packaging result. Evaluated against the version 2.0 specifications found on disk.

## Latest measured results and owner decisions

Owner selected Autumn, a female English voice, and the built-in microphone. Screenshots default to Pictures/Autumn; filename search to Documents and Downloads. Local runtime access and required downloads/cache writes were approved. The baseline download was explicitly allowed up to 60 minutes. No cloud inference, telemetry, administrator use, or Phase 1 approval was added.

| Experiment | Latest result | Evidence |
|---|---|---|
| Isolated environment | Python 3.14.6; pinned wheel-only dependencies installed with hash checks; all 11 component imports passed | requirements-phase0.lock; component_probe.json; dependency_manifest.json |
| Qt scope | PySide6-Essentials provides required bindings; full Addons download cancelled because unused WebEngine modules were delaying setup | D0004 |
| Source QML/tray | Pass using a local QML file, software renderer, and disabled QML disk cache | qt_smoke.json |
| Focus overlay | Test target held foreground and overlay preserved it | qt_smoke.json; this does not test elevated windows or real confirmation hotkeys |
| Native volume worker | Two current-volume set/read-back trials passed; owned worker termination and fresh restart passed | component_probe.json |
| Stop hotkey primitive | Temporary CTRL+ALT+F12 registration succeeded and was unregistered | component_probe.json; delivery/hold-to-talk/elevated-focus checks still pending |
| English female synthesis | Piper en_US-lessac-medium generated 10 valid WAVs; Windows Zira generated 10 test files | piper_tts.json; windows_tts.json; playback and owner quality not evaluated |
| Voice artifacts | Upstream revision, sizes, SHA256 recorded; ONNX checked against upstream LFS SHA256 | voice_artifacts.json; voice-specific dataset license still needs distribution review |
| Baseline model | qwen3:1.7b downloaded and verified by Ollama; digest and artifact size saved | baseline_model.json; inference and accuracy NOT measured |
| Existing model | User's gemma4:12b left untouched and unused | ollama_inventory.json |
| Standalone packaging | Build completed, executable launch failed on QtCore DLL import | packaging.json; attempts below |
| Antivirus | Command-line scan attempted with remediation disabled; exit 2, HRESULT 0x80508023 | defender_scan.json; scan is unverified, not clean |
| Recognition artifacts | base.en download completed and was checksum-verified before checkpoint cleanup; no captured audio, transcription or owner speech measurement | stt_base.en.json; small.en not downloaded; no recognition gate evidence |

### Packaging blocker: three attempts, then stop

1. PyInstaller standalone build of the working source probe: `ImportError: DLL load failed while importing QtCore: The specified procedure could not be found.`
2. Replaced only bundle-root VC runtime DLLs with the newer versions shipped by the hash-locked Qt wheel (14.44 versus bundle-root 14.42): same error.
3. Copied a coherent set of wheel-provided top-level Qt/shiboken DLLs into this disposable bundle's root: same error.

No system runtime files were changed. Comparing primary source/bundle DLL hashes found them identical; this did not establish the missing procedure's cause. An overly broad PE inspection was stopped at 60 seconds; a faster inspection produced incomplete export comparisons and is not accepted as root-cause proof. Do not continue the same repair loop.

The preferred pyside6-deploy route was also checked with `--dry-run --no-install`; it stopped because Nuitka was absent and warned that dumpbin was unavailable. PyInstaller was evaluated as a local alternative, not declared production-ready.

### Checkpoint decision required

Recommended: approve a fresh, bounded compatibility experiment with an older pinned Qt release and, if required, Python version, while retaining the safety rules and release gates. Alternative: explicitly approve the documented locked-environment launcher for the personal MVP and defer standalone delivery; that would require recording its effect on the Phase 0 gate rather than silently declaring a pass.

No Phase 1 work has started. Remaining model comparison/inference, CPU fallback, owner speech bake-off, wake evaluation, indexed-search coverage, app-catalog launches, hold-to-talk delivery, license closure and final schedule remain unverified. No numerical accuracy or latency claim is made.

### Source notes checked during this session

- [Qwen3.5 2B candidate](https://ollama.com/library/qwen3.5:2b): available candidate; not downloaded or selected.
- [pywhispercpp](https://pypi.org/project/pywhispercpp/): installed recognition binding candidate; no recognition run yet.
- [Piper Python API](https://github.com/OHF-Voice/piper1-gpl/blob/main/docs/API_PYTHON.md): synthesis adapter used for fixed test phrases.
- [Lessac voice model card](https://huggingface.co/rhasspy/piper-voices/blob/main/en/en_US/lessac/medium/MODEL_CARD): retain its dataset license link; repository-level licensing is not a substitute for voice-specific review.
- [PyInstaller manual](https://pyinstaller.org/en/stable/): alternative standalone packager evaluated; successful build alone did not establish a working executable.

## Initial read-only inventory (historical)

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
