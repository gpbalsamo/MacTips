# 10 — Hardware profiles

These profiles are examples to help you set expectations. They are **not
benchmarked results**: the capabilities listed are what each class of machine is
plausibly suited for, to be confirmed by measurement
([04](04-local-llm-with-ollama.md), [07](07-ecland-benchmark-cascade.md)).

Check your own machine with:

```bash
uname -m
sysctl -n hw.memsize
sysctl -n hw.ncpu
```

## Profile A — Developer laptop

Example: **Apple M3, 16 GB unified memory**

Suitable for:

- scientific coding
- small local tests
- smaller local LLMs (SMALL tier)
- learning and prototyping agent workflows
- Claude / Codex escalation

With 16 GB shared between macOS, your tools and the model, expect to use small
models, short contexts, and to close memory-hungry applications while running
inference. Lean on frontier escalation for anything hard.

## Profile B — Scientific AI node

Example: **Mac mini M5 Pro, 64 GB unified memory, 1 TB SSD**

Suitable for:

- persistent Ollama / MLX service
- larger quantized coding models (MEDIUM tier)
- longer context
- repository retrieval
- local agent orchestration
- concurrent diagnostics
- small scientific experiments
- evaluation of local-versus-frontier workflows

The extra memory allows a larger model *and* room for the build tools,
retrieval index and small model runs at the same time. The SSD holds several
multi-gigabyte model files and modest test datasets.

### What the node is for

The Mac mini is intended primarily for:

```
INFERENCE
ORCHESTRATION
SMALL EXPERIMENTS
VALIDATION
```

It is **not** intended to replace:

- GPU model training
- production Earth-system simulations
- high-resolution HPC workflows

Those belong on ECMWF HPC, and only when the smaller stages of the cascade
([07](07-ecland-benchmark-cascade.md)) have justified the cost.

## Choosing

| Question | Answer |
|----------|--------|
| Just want a working scientific Mac? | Any Apple-silicon Mac; follow [01](01-mac-scientific-setup.md)–[03](03-ecland-on-apple-silicon.md) |
| Want to try local LLMs and agents? | Profile A is enough to learn the workflow |
| Want a serious local repository agent? | Profile B class memory is where MEDIUM-tier models become practical, to be verified per model |
| Need to run production simulations or train models? | Use HPC / GPU resources |
