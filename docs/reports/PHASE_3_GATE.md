# Phase 3 checkpoint — 31 October 2026
Status: implementation COMPLETE; acceptance gate FAILED; stop here before Phase 4 (D0013).
| Check | Result and evidence |
|---|---|
| Functional software, UI, cancellation, private history, origin binding, packaging and disposable model-planned app launch | PASS — 324 tests / 31.27s, clean lint, source/standalone UI and one owned-window launch; `phase3_gate.json`, `phase3_native_e2e.json` |
| Pinned local model, live enums, one repair, no thinking, loopback/cloud boundary | PASS — qwen3:1.7b digest `8f68893c685c3ddff2aa3fffce2aa60a30bb2da65ca488b61fff134a4d1730e7`; runtime 0.33.2; CPU only, VRAM 0; model outputs never grant authority |
| NFR-01 supported skill and arguments | FAIL — 162/200 (81%; target 95%); conservative grammar/guard declines plus model skill/argument mistakes; `phase3_heldout_rc1.json` |
| NFR-02 unclear/unsupported handling | FAIL — 40/50 (80%; target 95%); some requests mapped to unrelated valid skills; zero actions dispatched during this trial; policy enforcement is separately property-tested |
| NFR-04 model warm latency / NFR-05 UI | NFR-04 NOT PASSED: GPU unverified; CPU p50 3.1806s / p95 4.9735s vs targets 3s / 6s. NFR-05 PASS; rendered input/Stop timings in `phase3_frozen.json` |
Evaluation: once-only locked RC1, 200 supported + 50 other text cases, including three owner examples; template-heavy data with limited owner provenance. No tuning from results. Exact commands remain available when the model is off/unavailable. Further routing changes require a fresh independent dataset; live voice and prior Phase 0/2 exceptions remain outstanding.
