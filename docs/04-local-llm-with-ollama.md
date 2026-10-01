# 04 — Local LLM with Ollama (and MLX)

## How local inference works

A large language model is a very large file of numbers (the *weights*). To
answer a prompt, software loads those weights into memory and computes the
reply one token at a time.

On an Apple-silicon Mac, CPU and GPU share one pool of **unified memory**. That
has practical consequences:

- **The model must fit in memory** alongside your other work. A model that does
  not fit will be slow or fail to load.
- **Quantization** stores weights with fewer bits (e.g. 4-bit instead of 16-bit)
  so a model needs roughly a quarter of the memory, at some cost in quality.
- **Context length** (how much text the model can consider at once) costs
  additional memory (the *KV cache*). Long repository-level context can be
  expensive.
- **Speed** depends mostly on memory bandwidth, so the same model runs at
  different speeds on different chips.

Rough rule of thumb (an approximation, not a guarantee): a 4-bit quantized model
needs somewhat over half a gigabyte per billion parameters for weights, plus
cache and overhead, and macOS does not let the GPU use all of unified memory.
Measure on your machine with `ollama ps`.

> **Hardware fit does not guarantee agent quality.**
> A model that loads and answers quickly may still fail at multi-step,
> tool-using repository work. **Every model must be benchmarked on real tasks**
> before it is trusted with any. See
> [07](07-ecland-benchmark-cascade.md) and
> [08](08-frontier-assisted-specialisation.md).

## Ollama

[Ollama](https://ollama.com) runs models locally and exposes them through a
command line and a local HTTP API (by default on `localhost` only).

Install from <https://ollama.com/download> (a Homebrew package also exists;
check `brew info ollama`). On a Linux / WSL2 node with an NVIDIA GPU, see
[11](11-rtx-linux-node.md): there the model must fit in GPU **VRAM**, which is
separate from system RAM. Then:

```bash
ollama list              # models downloaded to this machine
ollama ps                # models currently loaded, memory use, CPU/GPU split
ollama run <model>       # chat with a model (downloads it first if needed)
ollama pull <model>      # download without running
ollama stop <model>      # unload a model from memory
ollama rm <model>        # delete a downloaded model (destructive: confirm before an agent runs it)
```

Notes:

- Models are multi-gigabyte downloads. Treat a large pull as a **large
  download** and confirm first (see
  [09](09-security-and-safe-agent-use.md)).
- `ollama ps` is the honest indicator of fit: check that the model is loaded
  fully on the GPU and see how much memory it really takes at your context
  length.
- Keep the service bound to localhost unless you have a specific reason and a
  security plan.

Check what is installed, read-only:

```bash
./scripts/check_ai_stack.sh
```

## MLX / MLX-LM as an alternative

[MLX](https://github.com/ml-explore/mlx) is Apple's array framework for Apple
silicon, and [MLX-LM](https://github.com/ml-explore/mlx-lm) runs and serves
language models on it. It is a useful alternative when you want tighter control,
Python-level access, or models published in MLX format.

```bash
python3 -m venv ~/Work/mlx_venv
source ~/Work/mlx_venv/bin/activate
python -m pip install --upgrade pip
python -m pip install mlx-lm
```

See the MLX-LM documentation for the current command names and model formats;
they evolve quickly. Ollama is the simpler starting point; MLX is worth
evaluating if you want to go further.

## Capability tiers

Do not lock MacTips (or your workflow) to one model. Think in tiers.

### SMALL — roughly 7B–9B class

- summarisation
- basic code work
- simple file operations

Fits on a 16 GB machine. Expect to supervise it closely.

### MEDIUM — roughly 20B–35B quantized coding models

- a better target for repository-agent work (reading files, choosing tools,
  making small edits)
- requires more unified memory (see
  [10 — hardware profiles](10-hardware-profiles.md))

### FRONTIER — Claude / Codex / GPT-class services

- difficult reasoning
- complex debugging
- architecture
- review

These run remotely. See
[05 — frontier agents](05-frontier-agents-claude-codex.md) and remember the
privacy implications in [09](09-security-and-safe-agent-use.md).

## Models currently under evaluation

> **Non-binding.** This is a starting list of candidates, not a recommendation.
> It was compiled from general knowledge, **not** from benchmarks run by
> MacTips, and model names, sizes and availability change constantly. Check
> `ollama.com/library` for what actually exists today.

| Tier | Candidate families to try | Status |
|------|---------------------------|--------|
| SMALL | small general / coding models in the 7B–9B range | first results below |
| MEDIUM | recent open coding models in the ~20B–35B range (dense or mixture-of-experts) | not yet benchmarked |

### First results (RTX node, October 2026)

Measured with
[`scripts/benchmark_ollama_agent.py`](../scripts/benchmark_ollama_agent.py) on
the RTX node ([11](11-rtx-linux-node.md)): 6 agent tasks built from real ecLand
build and test failures, each run 3 times (temperature 0.3, 16k context,
Q4_K_M, all fully on the GPU). Each task has a deterministic validator. "With
evidence" counts only passes where the model read at least one file.

| Model | PASS | PASS with evidence | Notes |
|-------|------|--------------------|-------|
| `qwen2.5-coder:14b` | 7/18 | 5/18 | Escalated correctly 3/3; read a long validation log correctly 2/3 |
| `lfm2.5:8b` (8B MoE, ~1B active) | 4/18 | 2/18 | Fast, but often answered after one directory listing |
| `qwen2.5-coder:7b` | 2/18 | 0/18 | Chose `relax_tolerance` instead of escalating, 3/3 |

Observed across all three:

- **Repository navigation failed 0/18**: invented paths, repeated identical
  searches, or stopped early.
- **Diagnosis stopped at the surface error** (a symlink named in the ctest
  message) instead of the missing file behind it, 0/9.
- Passes without reading any file occurred; a PASS alone does not show the
  model worked from evidence.

What this supports: none of these models is ready to explore a repository on
its own. The 14B model is a candidate for narrow roles (reading a log,
recognising when to escalate) behind a small fixed set of actions
([06](06-hybrid-scientific-assistant.md),
[08](08-frontier-assisted-specialisation.md)). This is a small sample (6 tasks,
3 repeats, one prompt style); treat it as a first measurement, not a ranking.

Record results in machine-readable form with
[`scripts/benchmark_local_agent.py`](../scripts/benchmark_local_agent.py) and
put your chosen model in your own copy of
[`config/models.example.yaml`](../config/models.example.yaml).

## Local models are narrow assistants

A local model here is a *tool chooser*, not an authority. It selects among
deterministic actions; validators decide whether the outcome is acceptable
([06](06-hybrid-scientific-assistant.md)). When it is stuck, it escalates
([08](08-frontier-assisted-specialisation.md)).
