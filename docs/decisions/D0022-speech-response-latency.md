# D0022 — response latency optimization
Question: How can Autumn respond sooner without replacing the pinned brain or lowering speech confidence gates?
Options: Use a smaller speech model; optimize the existing CPU pipeline and startup preparation.
Choice: Keep small.en/qwen3:1.7b/female voice; use eight available CPU threads (interleaved median 3.0643→2.2893 s), continuous per-frame VAD, adjustable 450/800/1200 ms response pause, bounded silence trimming, startup-only speech priming without devices, and short truthful acknowledgments with full onscreen details. No-PID launches return the same unverified handoff without a futile two-second poll; known-PID verification remains.
Reason: The owner requested optimization. Synthetic endpoint wait fell by 0.45 s; primed synthesis measured 0.075 s. Preserve Stop/cancellation, 20-second capture and 15-second planning/confidence bounds; no GPU retries, new dependencies, cloud, held-out tuning or hardware acceptance claims.
