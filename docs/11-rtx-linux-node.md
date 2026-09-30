# 11 — RTX node: Linux (WSL2) with an NVIDIA GPU

MacTips is written for Apple silicon, but the same workflow runs on a Windows
PC with an NVIDIA RTX GPU, using Ubuntu under WSL2. This page records how such
a node (Profile C in [10](10-hardware-profiles.md)) was configured.

> **Status:** sections 3–5 and the `PATH` fix were run on one machine
> (Ubuntu 24.04 on WSL2, GeForce RTX 5060 Ti 16 GB, September 2026) and
> checked with the read-only scripts. The WSL settings and the PyTorch venv
> already existed there and were only verified (`torch.cuda.is_available()` is
> `True`), not re-created from these commands. Not tested on other GPUs or
> distributions; versions will drift.

## 1. Know your machine

```bash
uname -m                     # x86_64
cat /etc/os-release | head -3
nproc                        # logical CPUs visible to WSL
free -h                      # RAM visible to WSL (capped by .wslconfig)
nvidia-smi                   # GPU, VRAM, driver, CUDA version
nvidia-smi --query-gpu=name,memory.total,driver_version,compute_cap --format=csv
```

Unlike a Mac, **GPU memory (VRAM) and system RAM are separate**. A model that
fits in VRAM runs on the GPU; anything that spills over runs on the CPU from
system RAM and is much slower.

## 2. WSL2 specifics

- **GPU driver:** install the NVIDIA driver on **Windows** only. WSL2 passes it
  through as libraries in `/usr/lib/wsl/lib`. Do not install an NVIDIA driver
  inside Ubuntu. A CUDA toolkit inside Ubuntu is only needed to compile CUDA
  code; Ollama and PyTorch wheels bring their own CUDA runtime.
- **`nvidia-smi` not found:** it lives in `/usr/lib/wsl/lib`, which may be
  missing from `PATH` (e.g. when Windows interop / path appending is
  disabled). Add to `~/.profile`:

  ```bash
  if [ -d /usr/lib/wsl/lib ] ; then
      case ":$PATH:" in *:/usr/lib/wsl/lib:*) ;; *) PATH="$PATH:/usr/lib/wsl/lib" ;; esac
  fi
  ```

- **systemd** must be on for Ollama to run as a service. In `/etc/wsl.conf`:

  ```ini
  [boot]
  systemd=true
  ```

- **Memory and idle shutdown** are set on the Windows side in
  `%UserProfile%\.wslconfig`. Example used on the node:

  ```ini
  [wsl2]
  memory=13GB
  swap=16GB
  networkingMode=mirrored

  [general]
  instanceIdleTimeout=-1
  ```

  `memory` caps the RAM WSL can use; leave enough for Windows.
  `instanceIdleTimeout=-1` keeps WSL (and the Ollama service) running when no
  terminal is open. With `networkingMode=mirrored`, a port bound to
  `127.0.0.1` in WSL is also reachable at `localhost` on Windows, but not from
  the network. Run `wsl --shutdown` in Windows after editing this file.

- **sudo needs a real terminal.** A command that asks for a password cannot be
  run by an agent or through a non-interactive shell. Run installs yourself in a
  WSL terminal.

## 3. Scientific toolchain (apt)

The Ubuntu equivalent of [01](01-mac-scientific-setup.md):

```bash
sudo apt-get update
sudo apt-get install -y build-essential gfortran cmake ninja-build pkg-config \
  openmpi-bin libopenmpi-dev libnetcdf-dev libnetcdff-dev netcdf-bin \
  libeccodes-dev libeccodes-tools libaec-dev cdo python3-venv zstd
./scripts/check_science_stack.sh
```

On Ubuntu 24.04 this gave cmake 3.28, GCC/gfortran 13.3, OpenMPI 4.1.6,
ecCodes 2.34.1, NetCDF 4.9.2, CDO 2.4.0 and ninja 1.11, with every check
PASS. With the apt OpenMPI, `mpicc` / `mpifort` are on `PATH` and the Homebrew
`MPI_HOME` line in the ecLand4U notes is not needed.

## 4. Ollama with CUDA

`zstd` (above) is required by the installer. Then, in a terminal where you can
type your sudo password:

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

This installs to `/usr/local`, creates an `ollama` user and an `ollama`
systemd service, and binds the API to `127.0.0.1:11434`. Verify:

```bash
systemctl is-active ollama                  # active
ss -ltn | grep 11434                        # 127.0.0.1:11434, not 0.0.0.0
journalctl -u ollama | grep "inference compute"   # should name your GPU, library=CUDA
./scripts/check_ai_stack.sh
```

If the log line says `library=cpu`, the GPU was not found; check `nvidia-smi`
first.

Ollama picks a default context from VRAM size (4096 tokens on 16 GB). Longer
contexts must be requested per model or with `OLLAMA_CONTEXT_LENGTH`, and cost
VRAM; confirm with `ollama ps` that the model is still `100% GPU`.

### What fits in 16 GB VRAM

Roughly: SMALL-tier (7B–9B) models fit with room for context; ~14B models at
4-bit fit with moderate context; MEDIUM-tier (20B–35B) models mostly do **not**
fit fully and will split between GPU and CPU. Measure with `ollama ps`. As in
[04](04-local-llm-with-ollama.md), fitting says nothing about agent quality.

## 5. ecLand on WSL2: two known issues

Build as in [ecLand4U](https://github.com/gpbalsamo/ecLand4U), with the apt
OpenMPI (`CC=mpicc CXX=mpicxx FC=mpifort`, no `MPI_HOME`). Two problems were
found on the node.

### `mpirun` hangs at startup

Symptom: ecLand tests time out with nothing in `stdout.log` after the
`mpirun -np 1 ...` line; `mpirun -np 1 hostname` also hangs and ignores
SIGTERM.

Cause: hwloc's `gl` plugin (Ubuntu 24.04's hwloc) probes the WSLg display for
NVIDIA GPUs and hangs. Found by running
`mpirun --mca ess_base_verbose 10 ...` (it stalls in the `hnp` component
before networking starts) and then disabling hwloc plugins one at a time.
Restricting MPI to loopback does **not** help.

Fix, in `~/.profile`:

```bash
export HWLOC_COMPONENTS=-gl
```

Check: `timeout -s KILL 15 mpirun -np 1 hostname` prints the hostname and
exits 0.

### `ifsbench` tests "Not Run"

Symptom: `ctest -L ecland` reports the `ecland_ifsbench_*` tests as
`Not Run: Unable to find executable .../ifsbench_run.py`.

Cause: the ecLand4U build command passes
`--cmake="Python3_EXECUTABLE=..."`. `tests/ifsbench/CMakeLists.txt` creates
`build/ecland/tests/ifsbench/ifsbench_venv` and calls
`unset(Python3_EXECUTABLE)`, which clears only the normal variable, not the
cache entry. The `ifsbench_ecland` package is therefore installed into the
build-tools venv instead, and the test symlink points at an empty
`ifsbench_venv`. This is platform-independent and may also affect macOS
builds that use the same command.

Workaround, after the build:

```bash
build/ecland/tests/ifsbench/ifsbench_venv/bin/python -m pip install tests/ifsbench
```

### Result on the node

With the `HWLOC_COMPONENTS=-gl` fix, upstream ecLand at commit `87021f4`
passed `ecland_test_insitu_US-Ha1_1991-1996_dp` (73 s) and
`ecland_test_2D_EU-001_20220101-20220102_dp` (110 s) against the shipped
control files, at the tests' own tolerances. With the `ifsbench` workaround,
all 7 enabled `ecland_ifsbench_*` tests also passed (including the
multi-process and multi-thread variants; `v1_EU_forward` is disabled
upstream). Total 9/9.

A branch whose physics differs from upstream will fail these tests until its
control files are regenerated. Validate a new node against an upstream commit
first, so that node problems and code changes are not confused.

## 6. PyTorch and small training

PyTorch wheels built for CUDA run on the passed-through driver. Use a
dedicated venv (not system Python):

```bash
python3 -m venv ~/venvs/cuda
~/venvs/cuda/bin/pip install torch --index-url https://download.pytorch.org/whl/cu130
~/venvs/cuda/bin/python -c "import torch; print(torch.cuda.is_available(), torch.cuda.get_device_name(0))"
```

Choose the wheel index matching a CUDA version your driver supports
(`nvidia-smi` shows the maximum). Recent GPUs need recent wheels: an RTX 50xx
(compute capability 12.0) is not supported by old PyTorch builds.

Training that fits in VRAM (small models, fine-tuning, emulators on regional
or coarse grids) is a reasonable use of this node. The rule from
[07](07-ecland-benchmark-cascade.md) still applies: scale to HPC only when the
smaller stages justify it.
