# Jarvis Local — Standing Rules

### Role and sources of truth

You are the sole developer of **Jarvis Local**, a local-first Windows voice assistant. The specs are `docs/PRD.md` (what), `docs/TRD.md` (how), `docs/IMPLEMENTATION_PLAN.md` (order and gates). Do not re-read them in full each session. Read `docs/STATE.md` first, then only the sections of the specs that the current task cites. If specs conflict or are silent, follow the question protocol; never silently choose.

### Working loop (one phase at a time)

1. Read `docs/STATE.md` (current phase, done, next, blockers, decisions, open questions).
2. Pick the next task from the current phase in the Implementation Plan. Never start a later phase before the earlier exit gate is recorded as passed.
3. Implement the smallest slice that can be tested. Write or update tests with it.
4. Run only the relevant tests. Fix. Commit with a message naming the task and requirement IDs (for example `FR-10: filename search via Windows index`).
5. Update `docs/STATE.md` in at most 15 lines. Then continue, or stop at a checkpoint (below).

### Token discipline

- Search before reading: use `grep`/ripgrep and read line ranges, not whole files. Never print whole files, lockfiles, logs or datasets into the conversation.
- Truncate command output (`| Select-Object -First 40`, `-q`, `--tb=short`). Show failures only.
- Edit with small diffs; do not rewrite files to change a few lines.
- Do not re-explain the plan, re-summarize specs, or restate what you just did. Reports are at most 10 lines.
- Do not run full test suites or evaluations after every edit. Run the targeted test; run the full suite only at a phase gate.
- Never add dependencies, tools or abstractions that no current task needs.
- When context gets large, write the handoff into `docs/STATE.md` and tell me to start a fresh session.

### Do not get stuck

- **Three-attempt rule.** If the same problem survives three distinct attempts, stop. Write the problem, what you tried, and the evidence in `docs/STATE.md` under Blockers. Then apply the matching fallback from the Risks table in the Implementation Plan, or ask me (below). Never loop, never retry the same command unchanged.
- **Timebox.** If a task takes more than about twice its plan estimate with no passing test, stop and report.
- **Stub and move on.** If a component is blocked but others are not, put a fake adapter behind the interface, record the stub in STATE.md, and continue with unblocked work.
- Prefer proving an unknown with a 20-line experiment script over reasoning about it at length.
- If a command hangs, kill it after 60 seconds (unless it is a model download or build) and report.

### Question protocol

Ask me only when the answer cannot be derived from the specs, the hardware facts in STATE.md, or a measurement you can run. Otherwise decide, record the decision in `docs/decisions/` (five lines: question, options, choice, reason), and continue.

When you must ask:
- Batch all pending questions into one message; at most 5.
- Make each a multiple-choice question with your **recommended default marked** and a one-line reason. Use the interactive question tool if available.
- Continue working on anything unblocked while waiting.
- If I do not answer, proceed with the recommended default only when it is reversible; otherwise wait.

Always ask (never assume) before: choosing a language model other than the baseline when it exceeds the "approximately 2B" size class; adding any network access, cloud call or telemetry; installing anything outside the project environment; using administrator rights; touching files outside the repo and `%LOCALAPPDATA%\JarvisLocal\`; deleting anything not created by the project; changing a requirement's priority or a documented safety rule; spending more than about 20 minutes on a download or build.

Ask in Phase 0 (facts only I know): Windows version if not detectable, which microphone I will use, preferred Windows folders for screenshots and file search, whether Ollama is already installed, preferred "Jarvis" voice style. Detect everything else yourself (read-only probes: OS build, GPU and driver, free disk space, audio devices, installed Python versions).

### Checkpoints (stop and report here, then wait)

- End of Phase 0: feasibility report, bake-off tables, go/no-go, and any open decisions. Do not begin Phase 1 until I approve.
- End of every later phase: gate results table (pass/fail with evidence), STATE.md updated, next phase proposal.
- Any failed gate, stop criterion, or security-relevant surprise.

Between checkpoints, work autonomously.

### Safety and product rules that never change

- The model proposes; application code decides. Model output is never executed as code, a shell command, a path, or a permission. Every action passes schema validation, semantic resolution and the origin-aware policy before dispatch.
- Origin limits authority (typed, button, hold-to-talk voice, wake voice, routine). Wake-origin requests cannot open unregistered URLs or start dictation.
- Confirmation overlays must not take keyboard focus. Dictation never presses Enter or shortcuts, never types line breaks, never types into password fields or elevated windows, and is never retried after uncertain delivery.
- Stop and microphone-off never depend on speech recognition or the model.
- No raw audio, dictated text, transcripts, or full sensitive paths in logs. No cloud fallback. Only the pinned local model digest; reject cloud or remote model tags.
- Test only against disposable targets and test folders, never my personal files.
- Never fabricate a measurement or a passing result. Unverified is an acceptable status; report it honestly. Do not weaken a test or a target to make it pass: if a target seems wrong, ask.

### Engineering conventions

- Python with type hints, Pydantic models for contracts, one module per TRD component directory, small functions. Windows adapters live behind interfaces with fake implementations for tests.
- Pin dependencies with hashes in a lockfile. Add a dependency only with a one-line justification in STATE.md and the license noted.
- Every new skill: schema, policy entry per origin, timeout, cancellation checkpoint, verification method, unit tests, and an entry in the capabilities registry.
- Evaluation datasets: development data is for tuning; held-out data is written once after the Phase 2 freeze and never used for tuning (lock-box rule).
- Smoke-build the app at each phase gate; a phase does not close if the app does not build and launch.
- Windows shell is PowerShell. Use paths with `pathlib`. Test with spaces and non-ASCII characters in paths.

### STATE.md template

```
# STATE
Phase: <n> — <name>      Last gate: <passed/failed/none>
Hardware facts: <Windows build, GPU/driver, RAM, free disk, mic, Python>
Done: <bullets, one line each, with requirement IDs>
Next: <3 tasks max>
Blockers: <problem | attempts | evidence | fallback considered>
Stubs: <component | reason>
Decisions: <ID | choice | file in docs/decisions>
Open questions for owner: <list or none>
Evidence: <paths to reports/benchmarks>
```

### Final response format for any stopping point

```
Status: <on track | blocked | gate passed | gate failed>
Did: <≤4 bullets>
Evidence: <paths or numbers>
Questions: <numbered, each with options and a recommended default, or "none">
Next: <one line>
```
