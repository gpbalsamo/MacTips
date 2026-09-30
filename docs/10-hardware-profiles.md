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

On Linux / WSL2 (Profile C): `nproc`, `free -h`, `nvidia-smi`.

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

## Profile C — RTX node (Linux / WSL2)

Example: **Windows PC, NVIDIA GeForce RTX 5060 Ti 16 GB VRAM, Ubuntu 24.04
under WSL2, 13 GB RAM given to WSL, 1 TB SSD**

Setup: [11 — RTX node](11-rtx-linux-node.md).

Suitable for:

- persistent Ollama service with CUDA
- SMALL-tier models, and ~14B models at 4-bit, fully on the GPU
- local agent orchestration and validation, as for Profile B
- building and testing ecLand with the Ubuntu toolchain
- **small GPU training and fine-tuning** that fits in 16 GB VRAM (e.g. ML
  emulators on regional or coarse grids)

Differences from Profile B:

- VRAM is separate from system RAM. 16 GB of VRAM holds less than 64 GB of
  unified memory, so MEDIUM-tier models mostly split between GPU and CPU and
  slow down. Check with `ollama ps`.
- CUDA gives access to the mainstream ML stack (PyTorch, and frameworks built
  on it), which is why this profile includes small training.

Still **not** a replacement for production training, production Earth-system
simulations or high-resolution HPC workflows.

## Choosing

| Question | Answer |
|----------|--------|
| Just want a working scientific Mac? | Any Apple-silicon Mac; follow [01](01-mac-scientific-setup.md)–[03](03-ecland-on-apple-silicon.md) |
| Want to try local LLMs and agents? | Profile A is enough to learn the workflow |
| Want a serious local repository agent? | Profile B class memory is where MEDIUM-tier models become practical, to be verified per model |
| Want CUDA, or small training / fine-tuning next to the agent? | Profile C (RTX node), within its VRAM |
| Need to run production simulations or train large models? | Use HPC / GPU resources |
