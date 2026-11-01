# Timeout repair — D0024, 1 November 2026
Reproduced: loaded pinned brain, 0–16 ms metadata calls, but two opening requests hit 40 seconds; a 96-token probe exposed a repeated invented Spotify query URI.
Changed: concise example-led tool instructions, 256-token/20-second planning, immediate streamed repetition rejection, one bounded invalid-plan repair, validated empty inspect payloads and accurate TIMEOUT outcome codes.
Fast path: general-mode courtesy/addressing wrappers resolve through the unchanged exact native matcher; negation/compound/unknown requests retain their complete original model request, never a partial native action.
Measured after: same two model-only opening requests 3.766/1.344 seconds; date planning 1.547 seconds; real model→Get-Date→text answer 4.984 seconds. No microphone or voice playback timing is included.
Evidence: timeout_before.json, timeout_prompt_probe.json, timeout_after.json; fake native adapter checks confirm model bypass without opening personal apps.
Checks: 487/487 regression tests, lint clean; transport fixture verifies early connection close on repetition, independent cancellation and no uncertain-action replay retained.
Build: staged collection/copy resolves the Windows folder lock without stopping shared Ollama; 75 modules/UI/helper match. Source/frozen/installed normal/warm/scale2 UI and isolated install/remove pass, preserving owner fixtures; 0.8.1 installer/checksums delivered.
Profile: general control, automatic local brain and hands-free preferences remain enabled; no model/dependency/cloud/GPU/administrator change.
Limits: repair targets the reproduced regression; earlier file-task/accuracy failures and owner microphone/room/hardware/release acceptance remain separate, failed or pending; no RC1 reads/reruns.
