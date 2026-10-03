# 06 — The hybrid scientific assistant

This is the central page of MacTips. It describes how a small local model, a
set of deterministic tools, independent validators and an occasional frontier
model fit together.

> **Status:** mostly a design. One slice now runs end to end: a validator for
> ecLand test output, a read-only local diagnosis and an escalation package
> ([below](#a-first-working-slice-guarded_agentpy)). Retrieval, retries,
> frontier correction and exemplars are still to be built and measured.

## The architecture

```
                HUMAN
                  |
                  v
            local AI agent
                  |
        +---------+---------+
        |                   |
 deterministic tools     retrieval
        |                   |
        +---------+---------+
                  |
             scientific task
                  |
             validator
                  |
        +---------+---------+
       PASS                FAIL
        |                   |
       next         local retry <= limit
                            |
                       unresolved
                            |
                            v
                     frontier LLM
                            |
                      correction
                            |
                            v
                       validation
                            |
                            v
                    reusable exemplar
```

## The division of labour

```
THE LLM CHOOSES ACTIONS.

TOOLS PERFORM ACTIONS.

VALIDATORS DECIDE PASS/FAIL.
```

| Role | Who | Examples |
|------|-----|----------|
| Choose the next action | The local LLM | "inspect the log", "run the build", "run the site test" |
| Perform the action | Deterministic tools | `cmake`, `ctest`, a run script, a plotting script |
| Decide PASS/FAIL | Validators | exit codes, `ctest` results, water-budget closure checks, file / grid consistency checks |
| Set direction and accept results | The human | scope, thresholds, final sign-off |

The LLM should **never** decide that a water budget, a grid mapping or a
numerical result is acceptable based only on visual inspection of output.
Output that merely looks plausible is not scientific success.

## Components

### The human

Defines the task, approves anything outside the safe set in
[AGENTS.md](../AGENTS.md), and owns scientific acceptance criteria.

### The local AI agent

A small model (see [04](04-local-llm-with-ollama.md)) following the short
instructions in [AGENTS.md](../AGENTS.md). Its loop:

```
analyse
  → explain intended action
  → perform smallest useful action
  → validate
  → inspect git diff
  → report
```

### Deterministic tools

A *small, stable* vocabulary of actions the agent may invoke, for example:
`build`, `run`, `validate`, `plot`, `inspect-log`, `status`. Constraining the
action space is the single most effective way to make a small model reliable
([08](08-frontier-assisted-specialisation.md), stage A).

### Retrieval

Curated material the agent can look up rather than remember: build notes,
failure signatures, worked examples, the documentation of the scientific
repositories. Retrieval is where validated lessons accumulate.

### Validators

Programs, not opinions. A validator returns PASS or FAIL with evidence.
Examples: the build exits 0; `ctest -L ecland` reports the expected tests
passing; a run's output file exists, has the expected variables, dimensions and
time axis; a budget closes within a threshold that a **human** chose.

The agent does not invent scientific acceptance thresholds.

### Retry limit and escalation

On FAIL the agent may retry locally, up to a fixed limit (the default policy in
[`config/models.example.yaml`](../config/models.example.yaml) is 2). If the case
is still unresolved, the agent **stops** and prepares an escalation package:

- requested task
- current repository state
- commands attempted
- first meaningful error
- relevant log excerpt
- files inspected
- current hypothesis

The package is passed to a frontier model
([05](05-frontier-agents-claude-codex.md)). Check
[09](09-security-and-safe-agent-use.md) first: the package may leave your
machine, so it must contain only material you are authorised to send.

### Frontier correction, validation, exemplar

The frontier model diagnoses and proposes a fix. The fix is then run through
the **same validators**. Only if it passes does it become a reusable exemplar:
a documented case the local agent can later retrieve. A correction that has not
been validated is not knowledge.

## A first working slice: `guarded_agent.py`

[`scripts/guarded_agent.py`](../scripts/guarded_agent.py) implements the
validator → escalation path for ecLand tests, with the protection built into
the tools rather than written as a rule. Measurements showed why: with the
rules in the system prompt, local models still chose to relax tolerances,
regenerate reference data or revert commits
([04](04-local-llm-with-ollama.md#do-rules-in-the-system-prompt-make-models-escalate)).

1. **The validator decides.** A deterministic parser reads `ctest` output and
   returns PASS/FAIL per test and per validated variable. On PASS no model is
   called.
2. **FAIL always stops for a human.** The run writes an escalation package
   (task, verdict, repository state, first meaningful error, log excerpt,
   files inspected, hypothesis). The model does not decide whether to
   escalate.
3. **The model can only read.** Its actions are `find_files`, `search`,
   `inspect_log` and `show`, over a run directory holding the evidence. None
   can write, run commands or touch tolerances, reference data or commits.
   Its suggested next step is recorded for the human, and flagged as
   **protected** when it touches those items.

```bash
# validate an existing ctest log; diagnose with a local model on FAIL
python3 scripts/guarded_agent.py --ctest-log ctest.log --repo ~/ecland \
    --base <upstream-commit> --model gpt-oss:20b
# or run ctest in a build directory first
python3 scripts/guarded_agent.py --build-dir ~/ecland/build --repo ~/ecland \
    --ctest-regex ecland_test_ --model gpt-oss:20b
```

Exit status is 0 for PASS, 2 for FAIL (package written), 1 for a harness
error. Checked on real logs from the RTX node ([11](11-rtx-linux-node.md)):
upstream ecLand PASS (2/2 and 7/7 ifsbench), a fork with a physics change
FAIL with the exact failed variables, and an earlier MPI-hang run FAIL. On
that fork failure, `gpt-oss:20b` proposed updating the reference data and
tolerances; the package flagged it as protected, and no action could carry it
out.

## What this design deliberately does not do

- It does not let the local model judge scientific correctness.
- It does not let the agent run long simulations or submit HPC jobs without
  human confirmation.
- It does not depend on the local model being clever; it depends on tools and
  validators being reliable.
- It does not assume a particular model. Models are swappable
  ([04](04-local-llm-with-ollama.md)).

## Where to go next

- The staged set of real scientific tasks the assistant is measured on:
  [07 — ecLand benchmark cascade](07-ecland-benchmark-cascade.md).
- How escalations improve the local agent over time:
  [08 — frontier-assisted specialisation](08-frontier-assisted-specialisation.md).
- Illustrative measurement code:
  [`scripts/benchmark_local_agent.py`](../scripts/benchmark_local_agent.py).
