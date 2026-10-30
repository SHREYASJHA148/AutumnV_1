## Part B — Kickoff prompts

### Start (Phase 0)

```
Read CLAUDE.md and docs/STATE.md (create STATE.md from the template if missing).
Begin Phase 0 of docs/IMPLEMENTATION_PLAN.md. Detect hardware facts with read-only probes first.
Then ask me, in one batched message, only the facts you cannot detect.
Work through the Phase 0 tasks autonomously, following the token-discipline and three-attempt rules.
Stop at the Phase 0 checkpoint with the feasibility report and go/no-go. Do not start Phase 1.
```

### Resume or next phase

```
Read CLAUDE.md and docs/STATE.md. Continue with the current phase; do not re-read the full specs.
Work autonomously until the phase exit gate. Stop only at a checkpoint or when the question protocol says to ask.
```

### If it seems stuck or wasting tokens

```
Stop. Write the current problem, attempts and evidence into STATE.md Blockers (10 lines max).
Apply the fallback from the Risks table or give me a batched, multiple-choice question with a recommended default.
Do not continue the failing approach.
```

### Adding scope later

```
Add <skill> as a new skill. Follow the "every new skill" convention. Update the registry, policy matrix, tests and capabilities help.
Re-run only regression checks affected. Report in the standard format.
```
