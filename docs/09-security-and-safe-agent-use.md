# 09 — Security and safe agent use

An agent that can run commands can also delete files, leak secrets or launch
expensive jobs. A local model makes different mistakes from a frontier model,
but both can make them. This page describes the guardrails MacTips assumes.
The short version for a small local model is in [AGENTS.md](../AGENTS.md).

## What must never be exposed

- **Credentials and API keys** — for frontier services, cloud accounts, data
  portals.
- **GitHub tokens** and other personal access tokens.
- **SSH keys** (`~/.ssh`), including keys that give access to HPC systems.
- **Sensitive files** — `.env` files, shell history, browser profiles, private
  datasets, unpublished results, anything under an embargo or licence that
  forbids redistribution.

Practical measures:

- Keep secrets out of repositories. This repository's `.gitignore` excludes
  common local-config and secret files; keep your real values in those.
- Run agents from inside the project directory, not from `~`.
- Do not paste tokens into prompts, and do not put them in files an agent may
  read.
- Copy `config/*.example.yaml` to local, uncommitted files for real values.
- If a secret is exposed, revoke and rotate it; deleting it from a chat or a
  commit is not enough.

## Local versus external processing

**Local inference can keep content local.** With Ollama or MLX bound to
localhost, prompts and repository content stay on your machine (verify your own
configuration; do not assume).

**Frontier escalation may transmit repository context externally.** When a
local agent escalates to Claude, Codex or another hosted service, the escalation
package and anything the frontier agent reads or is shown may leave your
machine, and may be logged or retained under the provider's terms.

Therefore:

> Escalation packages must contain only material authorised for the external
> service.

Before escalating, review the package (see the format in
[`examples/hybrid-agent/escalation-package.example.md`](../examples/hybrid-agent/escalation-package.example.md)):

- Is the code or data licensed or permitted to be shared with that provider?
- Does any log excerpt contain paths, hostnames, usernames, tokens or data
  you would not post publicly?
- Is the package limited to what is needed (first meaningful error, relevant
  excerpt) rather than whole directories?
- Does your organisation's policy allow this provider for this material?

For sensitive or restricted work, prefer local-only handling, or ask the
relevant data owner before escalating.

## Actions that require confirmation

A human must approve each of these before an agent runs them:

| Action | Why |
|--------|-----|
| `rm` (especially recursive) | Deletes data, often irreversibly |
| `git clean` | Deletes untracked files, including uncommitted work |
| `git reset` (especially `--hard`) | Discards changes and history pointers |
| force push | Rewrites shared history |
| large downloads (datasets, model files) | Bandwidth, disk, licensing |
| HPC submission | Consumes shared, accounted resources |
| production simulations | Long, expensive, hard to interrupt cleanly |
| large data movement | Cost, integrity, and data-governance risk |
| installing system-wide packages | Changes the machine's state |
| editing credentials or config outside the repository | Security and blast radius |

The agent should **explain what it intends to do and why before asking**, so you
can judge the request rather than click through it.

## Review every change

After **any** modification by an agent, run:

```bash
git status
git diff
git diff --stat
```

Read the diff. Check that only the intended files changed, that nothing was
deleted unexpectedly, and that no secrets or absolute personal paths were
added. Commit only what you understand. Prefer small commits so that any single
step can be reverted.

## Do not trust plausibility

An agent — local or frontier — may report success that did not happen. Require
evidence: the command that was run, its output, and a validator's PASS/FAIL
([06](06-hybrid-scientific-assistant.md)). Output that merely *looks* plausible
is not scientific acceptance.

## Bounding the blast radius

- Work on a branch; keep the working tree clean before starting so `git diff`
  shows only the agent's changes.
- Give the agent the narrowest permissions your tool allows, and read what you
  approve.
- Keep long simulations and remote submissions manual.
- Run experiments on copies of data, not the only copy.

Related: [05 — frontier agents](05-frontier-agents-claude-codex.md),
[06 — hybrid assistant](06-hybrid-scientific-assistant.md).
