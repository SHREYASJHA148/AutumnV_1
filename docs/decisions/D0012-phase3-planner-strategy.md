# D0012 — Retain one-call structured planning
Question: Does a separate skill-selection call improve the small model enough to justify its latency?
Options: One schema-constrained call with deterministic/intent guards; select a skill and then generate arguments.
Choice: Retain one call: development v2 reached 36/37 overall (one article-normalization issue subsequently fixed), all eight warm model-path cases correct, p50 2.798s; the two-call prototype selected 3/4 skills correctly at p50 3.984s.
Reason: Two calls added latency and misselected mute as volume; its score checks skill selection only, not full argument accuracy. Keep CPU profile disclosed and GPU latency unverified; freeze before the held-out trial and never tune from held-out results.
