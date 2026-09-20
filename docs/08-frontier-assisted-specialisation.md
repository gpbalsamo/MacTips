# 08 — Frontier-assisted specialisation

How does a small, generic local model become a *useful* assistant for a
specific scientific codebase? Not by hoping. By a loop in which a frontier model
teaches it through validated examples, and in which every claim of improvement
is measured.

> **Status:** this is a proposed method. It has not yet been run at scale, and
> no improvement is claimed here. Each stage should be validated
> experimentally ([07](07-ecland-benchmark-cascade.md)).

```
   A CONSTRAIN
        ↓
   B FRONTIER TEACHER      ←──────────────┐
        ↓                                 │
   C REUSABLE SKILLS                      │
        ↓                                 │
   D BENCHMARK                            │
        ↓                                 │
   E CONTINUOUS CORRECTION ───────────────┘
        ↓
   F OPTIONAL FINE-TUNING
```

## A. CONSTRAIN

Reduce what the local model has to get right by exposing a **small set of
stable, deterministic actions**:

- `build`
- `run`
- `validate`
- `plot`
- `inspect-log`
- `status`

Each action is a script or command that behaves the same way every time, prints
clear output and returns a meaningful exit code. The model chooses *which* to
call and interprets *structured* results; it does not compose long ad-hoc shell
pipelines. This is the most effective early improvement, because it turns an
open-ended problem into a menu.

## B. FRONTIER TEACHER

When the local model fails, a frontier model (Claude, Codex or another) solves
the case, via the escalation package from [06](06-hybrid-scientific-assistant.md)
and the workflow in [05](05-frontier-agents-claude-codex.md).

Record the trajectory:

- **evidence read** — files and log lines inspected
- **diagnosis** — what was wrong, and why
- **commands** — what was run
- **edit** — the change made
- **validation** — how it was checked, with output
- **outcome** — PASS or FAIL

A solution is only a lesson if it validated. An unvalidated fix goes back to
the teacher, not into the knowledge set.

Before recording anything, review it under
[09 — security](09-security-and-safe-agent-use.md): trajectories must not contain
credentials or material that should not be stored or shared.

## C. REUSABLE SKILLS

Convert successful trajectories into durable, inspectable assets:

- **`AGENTS.md` instructions** — short rules for recurring situations
- **examples** — complete worked cases in `examples/`
- **tool recipes** — the exact action sequence for a task type
- **failure signatures** — "this error text means this cause; do this"
- **retrieval documents** — searchable notes the agent can look up
- **tests** — validators that catch the failure automatically next time

Keep `AGENTS.md` short (a small model has limited attention). Put detail in
retrieval documents and examples.

## D. BENCHMARK

Re-test the local model on **unseen but related** tasks — not on the exact case
it was just taught, which would only measure memorisation. Measure:

| Metric | Meaning |
|--------|---------|
| Autonomous completion | Fraction of tasks finished correctly without escalation |
| Correct escalation | When it could not solve a task, did it stop and escalate properly? |
| False success | Did it claim PASS where the validator says FAIL? (The most important number.) |
| Time / iteration | Wall-clock time and number of steps used |
| Frontier usage avoided | Escalations that were no longer needed |

Machine-readable records follow the shape in
[`scripts/benchmark_local_agent.py`](../scripts/benchmark_local_agent.py). Keep a
held-out set of tasks that is never used as a teaching example.

A **false success** is worse than a failure: it is a wrong result presented as
right. Track it explicitly.

## E. CONTINUOUS CORRECTION

Failed local-agent trajectories return to the frontier teacher, which diagnoses
what went wrong, including where the local agent went off track. The correction
is validated as in B. **Only validated corrections enter the knowledge set.**

Over time the set of escalations should shrink for well-covered task types and
remain for genuinely new ones.

## F. OPTIONAL FINE-TUNING

Only after a sufficiently large, high-quality dataset exists should
LoRA / QLoRA fine-tuning be evaluated.

```
Fine-tuning is NOT the first step.
```

Most early gains should come from:

- context
- tools
- retrieval
- examples
- workflow design
- failure signatures
- deterministic validators

Fine-tuning may later improve:

- tool choice
- failure classification
- workflow sequencing
- domain terminology
- escalation behaviour

**Do not rely on fine-tuning to encode scientific truth.** Scientific truth and
acceptance criteria belong in tested software, documentation and validators,
where they can be inspected, versioned and corrected. A fine-tuned model cannot
be audited the same way.

Fine-tuning itself is also a **cost decision**: it needs a curated dataset,
compute that a compact Mac may not offer (see
[10 — hardware profiles](10-hardware-profiles.md)), and a benchmark to prove it
helped. Compare against the cheaper options above before starting.

## Summary

```
constrain  →  teach  →  capture  →  measure  →  correct  →  (maybe) fine-tune
```

Each step is validated by tools, not by the model's own confidence.
