# Autumn 0.7.2 — response latency
- Same small.en recognition model, pinned qwen3:1.7b brain, female voice and confidence/policy gates; no new dependencies, downloads, GPU retries or Windows power changes.
- Controlled same-PCM CPU sweep: four-thread median 3.0643 s → eight-thread median 2.2893 s (25.3% lower); all six decodes exact. Separate before/after process runs have cache/load differences and are not the controlled percentage.
- Continuous VAD/trim: synthetic speech-end wait 0.9272 → 0.4772 s; final sound preserved; three simulated 48 kHz clipped utterances decoded exactly. Quick/Natural/Longer timing options retain bounded silence safeguards.
- Speech components prime without audio devices during voice-enabled startup; primed synthesis measured 0.075 s. Representative unverified spoken acknowledgment shrank from 6.014 to 2.345 s of generated audio, with full details onscreen.
- No-PID launches no longer poll two seconds for an impossible window match; outcome remains unverified, while known-PID verification and Stop/cancellation behavior remain tested.
- Software: 456 unique passing tests (450 full plus six new cases), including preservation of speech priming/acoustic tail when enabling listening; 71 bundled modules/UI match source; source UI under speech load p95 input/Stop 16/15 ms. Packaged speech/installer/UI evidence is in latency_optimization.json.
- Existing C:\adu\Autumn.lnk targets the rebuilt app. Previous preferences are retained; schema 9 applies Quick replies by default on next launch. No microphone or speakers opened in tests.
- Scope: synthetic component timings, not measured owner end-to-end speed or passing release acceptance. Prior accuracy/hardware/GPU/offline/clean-account/stability gaps remain. Questions: none.
