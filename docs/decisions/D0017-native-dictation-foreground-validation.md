# D0017 — Unattended foreground refusal
Question: What should happen when Windows refuses the disposable target's foreground switch during unattended validation?
Options: Force or bypass Windows foreground restrictions; preserve the guard and defer the interactive native typing trial.
Choice: Preserve the guard. Three controlled attempts (fixture launch, direct reproduction, Qt-owned driver) were refused by Windows. Source password-control refusal passed; immutable grants, control rejection, Unicode packet construction, focus loss and cancellation are tested with fake adapters. Native target delivery/overlay focus validation remains unverified.
Reason: Do not inject into an unverified foreground or work around Windows permissions. Record the failed native probe; continue unblocked implementation and Phase 6 under D0016, without claiming a passed Phase 5 acceptance gate.
