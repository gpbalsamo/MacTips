# MacTips

## Turn an Apple-silicon Mac into a scientific development and AI-assistant workstation

MacTips is a practical guide for configuring a modern Apple-silicon Mac for
scientific software development, local AI inference and AI-assisted
Earth-system model development.

The project started as a collection of macOS scientific-computing setup notes.
It now expands that idea to the question:

> How can a scientist turn a compact Mac into a useful scientific assistant,
> while keeping frontier AI and HPC for the tasks that genuinely need them?

The aim is not to replace frontier AI or HPC.

The aim is to use the right resource for the right task.

```
START LOCAL.
VALIDATE EARLY.
ESCALATE INTELLIGENTLY.
SCALE ONLY WHEN JUSTIFIED.
```

The central principle:

- Keep routine, bounded and repetitive development **local**.
- Use **frontier models** for difficult reasoning.
- Use **ECMWF HPC** for production-scale computation.

---

## 1. Why local AI?

A local model running on your own Mac has properties that a hosted service does
not:

- **Privacy** — content stays on the machine unless you choose to send it out.
- **Availability** — no network, quota or service dependency for routine work.
- **Cost** — repetitive, bounded tasks cost electricity, not tokens.
- **Control** — you choose the model, the context, the tools and the limits.

A local model also has limits. It is smaller, less capable at multi-step
reasoning, and more likely to be confidently wrong. **Hardware fit does not
guarantee agent quality.** The local assistant in MacTips is therefore
deliberately *narrow*: it chooses among a small set of deterministic tools,
and something other than the model decides whether the result is acceptable.

A local LLM is **not** presented here as a replacement for Claude, Codex,
domain experts, or HPC.

## 2. A hybrid development model

```
                     SCIENTIFIC MAC
                           |
              +------------+------------+
              |                         |
       Scientific stack             AI stack
              |                         |
     Python / MPI / NetCDF        Ollama / MLX
     ecCodes / CDO / ecLand      Local coding LLM
              |                         |
              +------------+------------+
                           |
                    Local AI agent
                           |
                  routine development
                           |
                 +---------+---------+
                 |                   |
               PASS              difficult case
                 |                   |
                 v                   v
            next local task     Claude / Codex
                                     |
                                     v
                            frontier reasoning
                                     |
                                     v
                              ECMWF HPC when
                           large compute is needed
```

The full architecture is described in
[docs/06-hybrid-scientific-assistant.md](docs/06-hybrid-scientific-assistant.md).

## 3. Three levels of use

You can stop at any level. Each one is useful on its own.

| Level | What you get | Guides |
|-------|--------------|--------|
| **1. Scientific workstation** | A Mac that builds and runs scientific software: Python stack, MPI, ecCodes, NetCDF, CDO, ecLand | [01](docs/01-mac-scientific-setup.md), [02](docs/02-python-and-science-stack.md), [03](docs/03-ecland-on-apple-silicon.md) |
| **2. Local AI workstation** | Local LLM inference (Ollama / MLX) and access to frontier coding agents | [04](docs/04-local-llm-with-ollama.md), [05](docs/05-frontier-agents-claude-codex.md) |
| **3. Scientific assistant** | A local agent that drives deterministic scientific tools, validated by tests, escalating to a frontier model when stuck | [06](docs/06-hybrid-scientific-assistant.md), [07](docs/07-ecland-benchmark-cascade.md), [08](docs/08-frontier-assisted-specialisation.md) |

## 4. Frontier models remain part of the architecture

Claude Code and Codex are repository-aware coding agents, not just chat
interfaces. They read the repository, propose actions, run commands with your
approval, and edit files. MacTips uses them for what small local models do
poorly: difficult debugging, architecture, and review. One frontier model can
also review work produced by another.

See [docs/05-frontier-agents-claude-codex.md](docs/05-frontier-agents-claude-codex.md).

## 5. Frontier-assisted specialisation

When the local agent fails on a case, a frontier model solves it. The
*validated* solution is then converted into reusable material: instructions,
examples, tool recipes, failure signatures, retrieval documents and tests. The
local agent is re-benchmarked on unseen but related tasks. Fine-tuning is an
optional, late step — **not** the first step.

See [docs/08-frontier-assisted-specialisation.md](docs/08-frontier-assisted-specialisation.md).

## 6. ecLand as a worked scientific example

[ecLand](https://github.com/ecmwf-ifs/ecland) is ECMWF's land-surface model.
It is used here because it offers a natural ladder of progressively larger,
progressively more expensive validation cases:

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

MacTips does not duplicate the scientific repositories. It explains how an
assistant can orchestrate them:

- [ecLand4U](https://github.com/gpbalsamo/ecLand4U) — building and running ecLand on a Mac
- [plumber2-ecland](https://github.com/gpbalsamo/plumber2-ecland) — site level
- [liaise-ecland](https://github.com/gpbalsamo/liaise-ecland) — regional
- [wfde5-ecland](https://github.com/gpbalsamo/wfde5-ecland) — global

See [docs/03-ecland-on-apple-silicon.md](docs/03-ecland-on-apple-silicon.md) and
[docs/07-ecland-benchmark-cascade.md](docs/07-ecland-benchmark-cascade.md).

## 7. Hardware profiles

- **Profile A — developer laptop** (e.g. Apple M3, 16 GB): scientific coding,
  small tests, smaller local models, prototyping agent workflows.
- **Profile B — scientific AI node** (e.g. Mac mini M5 Pro, 64 GB): persistent
  local inference, larger quantized coding models, longer context, retrieval,
  agent orchestration and small experiments.

Neither replaces GPU training, production Earth-system simulation or
high-resolution HPC workflows. See
[docs/10-hardware-profiles.md](docs/10-hardware-profiles.md).

## 8. Safety

Agents that can run commands can also do damage, and frontier escalation can
transmit repository content to an external service. MacTips therefore ships a
short [AGENTS.md](AGENTS.md) safety contract and a fuller guide:
[docs/09-security-and-safe-agent-use.md](docs/09-security-and-safe-agent-use.md).

The rule of thumb: **analyse first, modify second, test every change**, and
after any modification run `git status`, `git diff` and `git diff --stat`.

## 9. Quick start

All diagnostic scripts are read-only and install nothing.

```bash
git clone https://github.com/gpbalsamo/MacTips.git
cd MacTips

# What is installed on this machine?
./scripts/bootstrap_mac.sh --check
./scripts/check_science_stack.sh
./scripts/check_ai_stack.sh
```

Then follow, in order:

1. [docs/01-mac-scientific-setup.md](docs/01-mac-scientific-setup.md)
2. [docs/02-python-and-science-stack.md](docs/02-python-and-science-stack.md)
3. [docs/03-ecland-on-apple-silicon.md](docs/03-ecland-on-apple-silicon.md)
4. [docs/04-local-llm-with-ollama.md](docs/04-local-llm-with-ollama.md)

Copy `config/models.example.yaml` and `config/paths.example.yaml` to local,
uncommitted files and fill in your own values.

## 10. Historical documentation

The original MacTips notes (macOS 10.15 Catalina, MacPorts) are preserved
unchanged in
[docs/archive/macos-catalina-macports.md](docs/archive/macos-catalina-macports.md).
They are kept for reference; the new guides use Homebrew on Apple silicon.

## 11. Project philosophy

```
Scientific Mac
       ↓
Local LLM
       ↓
Repository-aware local agent
       ↓
Deterministic scientific tools
       ↓
Small validated experiments
       ↓
Frontier-model escalation when needed
       ↓
HPC only when scale requires it
```

```
START LOCAL.
VALIDATE EARLY.
ESCALATE INTELLIGENTLY.
SCALE ONLY WHEN JUSTIFIED.
```

- The LLM chooses actions. Tools perform actions. Validators decide PASS/FAIL.
- Plausible-looking output is not scientific success.
- Claims in these guides are marked as verified only when they have been run.

## Documentation index

| Document | Topic |
|----------|-------|
| [AGENTS.md](AGENTS.md) | Short instructions and safety contract for a local coding agent |
| [docs/01-mac-scientific-setup.md](docs/01-mac-scientific-setup.md) | Homebrew-based scientific setup |
| [docs/02-python-and-science-stack.md](docs/02-python-and-science-stack.md) | Python environments and packages |
| [docs/03-ecland-on-apple-silicon.md](docs/03-ecland-on-apple-silicon.md) | Building and testing ecLand |
| [docs/04-local-llm-with-ollama.md](docs/04-local-llm-with-ollama.md) | Local inference with Ollama / MLX |
| [docs/05-frontier-agents-claude-codex.md](docs/05-frontier-agents-claude-codex.md) | Claude Code and Codex workflow |
| [docs/06-hybrid-scientific-assistant.md](docs/06-hybrid-scientific-assistant.md) | The hybrid architecture |
| [docs/07-ecland-benchmark-cascade.md](docs/07-ecland-benchmark-cascade.md) | Progressive ecLand validation |
| [docs/08-frontier-assisted-specialisation.md](docs/08-frontier-assisted-specialisation.md) | Turning frontier fixes into local capability |
| [docs/09-security-and-safe-agent-use.md](docs/09-security-and-safe-agent-use.md) | Credentials, data and safe agent use |
| [docs/10-hardware-profiles.md](docs/10-hardware-profiles.md) | Laptop and Mac mini profiles |
| [docs/archive/macos-catalina-macports.md](docs/archive/macos-catalina-macports.md) | Original Catalina / MacPorts notes |
