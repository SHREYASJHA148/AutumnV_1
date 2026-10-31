# Evaluation boundaries

`docs/contracts/phase2-skills.json` freezes the version 1 skill names, argument definitions and declarations at the Phase 2 gate. Its checksum is in `docs/contracts/phase2-freeze.json`. Nine skills are active; dictation and routines remain reserved and disabled until Phase 5. Dynamic planner enums in Phase 3 may narrow these definitions to reviewed live registry IDs.

Development data is for tuning. Held-out input is never opened to guide tuning. The initial held-out file is `.cache/evaluation-lockbox/starter-heldout.json`; it contains 15 supported and five ambiguous/unsupported cases, was authored only after the schema freeze, has not been evaluated, and is read-only under a directory restricted to the current Windows user. Only its hash and counts are committed. Do not print or open its contents during development.

This starter is not the completed release dataset. Author additional independent, disjoint shards once, without reading the starter for inspiration; retain the starter unchanged. Include owner wording and other-person/tool wording before the first release-candidate evaluation. The target remains 200 supported plus 50 ambiguous/unsupported cases. Store additional shard hashes and access restrictions in the manifest. No audio or personal transcripts belong in Git.

Routing evaluation does not execute actions. The private catalog contains symbolic test IDs, not real launch paths. A runner must report deterministic and model paths separately and combined, skill/argument accuracy, ambiguity handling, latency and failure categories. Do not claim the held-out targets from development tests or these starter counts.

Inspect held-out results once per release candidate. If used for tuning, retire the affected dataset and author a new independent set. A change to the frozen skill/argument definitions requires an explicit recorded revision and dataset compatibility review. Phase 0 development measurements remain development measurements.
