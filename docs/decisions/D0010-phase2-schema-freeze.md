# D0010 — Phase 2 skill and argument freeze
Question: What is frozen before small-model integration and held-out evaluation?
Options: Change action definitions during model tuning; freeze the version 1 declarations and argument vocabulary first.
Choice: Freeze docs/contracts/phase2-skills.json with the hash in phase2-freeze.json; nine active skills and two reserved/disabled Phase 5 skills; create an unevaluated 20-case held-out starter only after this freeze.
Reason: Preserve an independent evaluation boundary. Starter data stays private/read-only and is never used for tuning; additional independent shards must reach 200 supported and 50 ambiguous/unsupported cases before release evaluation. Windows Search coverage remains unverified; the measured bounded-scan backend is the working fallback on this laptop.
