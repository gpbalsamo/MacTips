# 07 — The ecLand benchmark cascade

A local assistant should earn trust on cheap, fast, unambiguous tasks before it
is allowed near expensive ones. ecLand offers a natural ladder: each level is
larger, slower and more scientifically demanding than the one below.

MacTips does **not** duplicate the scientific repositories. It explains how an
assistant can orchestrate them. The repositories are the source of truth for
data, scripts and scientific content.

> **Status:** this page describes a progression to be built and measured. The
> repository descriptions below were taken from each repository's own README
> when this page was written; those projects evolve, so check them for current
> status. No level of this cascade has been run by an agent yet.

## The progression

```
ecLand code change
        ↓
ctest
        ↓
one PLUMBER2 site
        ↓
small PLUMBER2 subset
        ↓
LIAISE smoke test
        ↓
short WFDE5 global test
        ↓
CaMa-Flood
        ↓
production HPC only when justified
```

A change moves up only if it passes the level below. A failure is cheaper to
find at Level 0 than at Level 3.

## Levels

### LEVEL 0 — ecLand build + tests

- **Question:** does it compile, and do ecLand's own tests pass?
- **Guide:** [03 — ecLand on Apple silicon](03-ecland-on-apple-silicon.md);
  build workflow in [ecLand4U](https://github.com/gpbalsamo/ecLand4U).
- **Validator:** build exit status; `ctest -L ecland --output-on-failure`.
- **Cost:** minutes. Local.

### LEVEL 1 — PLUMBER2-ecland (SITE)

- **Repository:** <https://github.com/gpbalsamo/plumber2-ecland>
- **Scope:** single-point (site-level) simulations at flux-tower sites from the
  PLUMBER2 network, compared with observations. Its README describes running one
  site directly, a curated subset, or the full set of sites on HPC.
- **Ladder within the level:** one site → small subset → larger set. Start with
  **one site**.
- **Validator:** completion of the run, presence and structure of output, and
  the repository's own benchmark comparison, with acceptance thresholds set by a
  human.
- **Cost:** minutes per site. Local for one site or a small subset.

### LEVEL 2 — LIAISE-ecland (REGION)

- **Repository:** <https://github.com/gpbalsamo/liaise-ecland>
- **Scope:** a regional configuration (the Ebro basin in north-eastern Spain
  according to its README), with optional river-routing coupling and benchmarking
  against discharge observations.
- **Local use:** a **smoke test** (short period, checking that the chain runs and
  the outputs are well-formed), not the multi-decade production run.
- **Cost:** a smoke test is local; the full simulation is an HPC-scale job and
  requires human confirmation.

### LEVEL 3 — WFDE5-ecland (GLOBAL)

- **Repository:** <https://github.com/gpbalsamo/wfde5-ecland>
- **Scope:** a global chain from WFDE5 forcing through ecLand, with routing.
  Its README describes a staged approach: one-day, one-month, then one-year
  pilots before any multi-decade run.
- **Local use:** a **short global test** at most. At the time of writing, that
  README reports that only the one-day pilot had been run successfully; treat
  everything beyond it as not yet demonstrated.
- **Cost:** large forcing downloads and heavy runs. Downloads and long runs
  require confirmation ([09](09-security-and-safe-agent-use.md)).

### LEVEL 4 — CaMa-Flood (ROUTING / HYDROLOGY)

- **Scope:** river routing of ecLand runoff, and the resulting discharge and
  hydrology.
- **Note:** LIAISE and WFDE5 above already couple to CaMa-Flood; this level is
  where the routing itself is the object of validation.
- **Cost:** high. Production use belongs on HPC.

## Related

- [ecLand4U](https://github.com/gpbalsamo/ecLand4U) — building and running ecLand
  on a Mac, examples and diagnostics.

## How the assistant uses the cascade

For each level, the assistant needs:

1. **Deterministic tools** — `build`, `run`, `validate`, `plot`, `inspect-log`,
   `status` wrappers around the repository's scripts
   ([06](06-hybrid-scientific-assistant.md)).
2. **A validator** — a program that returns PASS/FAIL with evidence. Acceptance
   thresholds come from the scientific owners of each repository, never from
   the model.
3. **A cost gate** — anything long, large or remote (full runs, big downloads,
   HPC submission) needs explicit human confirmation.
4. **A benchmark record** — machine-readable results (see
   [`scripts/benchmark_local_agent.py`](../scripts/benchmark_local_agent.py)):
   did the local agent complete the task, did it escalate correctly, did it
   report success falsely?

## Measuring the local agent against the cascade

Suggested progression of *agent* tasks (to be built), from simple to hard:

| Task type | Example | Level |
|-----------|---------|-------|
| Repository navigation | "Where is the site-run script and what does it need?" | any |
| Build diagnosis | Read a failed build log; identify the first meaningful error | 0 |
| Guided run | Run one PLUMBER2 site via the documented script and validate the output | 1 |
| Regression check | After a small code change, decide which levels must be re-run | 0–2 |
| Failure escalation | Recognise it cannot fix a failure and produce a correct escalation package | any |

A first set of these tasks (build diagnosis, log reading, repository
navigation, failure escalation) exists in
[`scripts/benchmark_ollama_agent.py`](../scripts/benchmark_ollama_agent.py),
with fixtures in `benchmarks/fixtures/` taken from real ecLand failures. First
results are in [04](04-local-llm-with-ollama.md#first-results-rtx-node-october-2026).

Frontier-assisted improvement of these results is covered in
[08](08-frontier-assisted-specialisation.md).

## Production HPC only when justified

Reaching HPC scale should be the *end* of a chain of cheaper passes, not the
first attempt. Submitting to HPC, starting long simulations and moving large
data always require human confirmation.
