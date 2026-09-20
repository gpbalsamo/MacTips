# 03 — ecLand on Apple silicon

[ecLand](https://github.com/ecmwf-ifs/ecland) is ECMWF's land-surface model.
This page summarises how to build and test it on an Apple-silicon Mac. It
follows the procedure already documented in
[ecLand4U](https://github.com/gpbalsamo/ecLand4U); that repository is the
source of truth, and this page should not diverge from it.

## How to read this page

Two labels are used throughout:

- **VERIFIED WORKFLOW** — the procedure documented in ecLand4U, where it was
  run by its author on a Mac. It was **not re-run** while writing this page,
  so re-check against ecLand4U if you hit a problem.
- **MACHINE-DEPENDENT ADVICE** — reasonable guidance that may need adapting to
  your macOS version, Homebrew state, compilers or ecLand revision. Treat it as
  a hint, not a guarantee.

Nothing here claims that all ecLand tests pass on every machine or every ecLand
revision. Always read your own `ctest` output.

Prerequisites: [01 — Mac scientific setup](01-mac-scientific-setup.md)
(Homebrew, `open-mpi`, `cmake`, a Fortran compiler).

---

## VERIFIED WORKFLOW

### 1. Clean Python environment

```bash
conda deactivate 2>/dev/null || true

python3 -m venv ~/Work/ecland_venv
source ~/Work/ecland_venv/bin/activate

python -m pip install --upgrade pip
python -m pip install fypp

which python
which fypp
python --version
```

`fypp` is the Fortran pre-processor used by the build.

### 2. Environment variables

```bash
export PYTHONNOUSERSITE=1

export MPI_HOME=$(brew --prefix open-mpi)
export PATH="$MPI_HOME/bin:$PATH"

export CC=mpicc
export CXX=mpicxx
export FC=mpifort

export DR_HOOK_ASSERT_MPI_INITIALIZED=0
```

### 3. Clone ecLand

```bash
cd ~/Work
git clone https://github.com/ecmwf-ifs/ecland.git
cd ecland
```

### 4. Create the bundle and build

```bash
./ecland-bundle create

./ecland-bundle build \
  --cmake="Python3_EXECUTABLE=$(which python);FYPP=$(which fypp)"
```

### 5. Install

```bash
./build/install.sh --fast
```

### 6. Test

```bash
cd build
. ./env.sh
ctest -L ecland --output-on-failure
```

Use `-L ecland`. A bare `ctest` also runs the tests of the bundled
dependencies, which is usually not what you want.

Afterwards, run the read-only check:

```bash
./scripts/check_ecland_build.sh ~/Work/ecland   # from the MacTips directory
```

---

## MACHINE-DEPENDENT ADVICE

- **Debug build.** ecLand4U documents a debug configuration for tracing
  numerical problems: build with `--build-type=Debug --without-omp
  --without-tests` and add Fortran flags such as
  `-g -O0 -fcheck=all -fbacktrace` through `--cmake=ECBUILD_Fortran_FLAGS=...`.
  Take the exact invocation from ecLand4U rather than from this summary.
- **Shell state matters.** The build is sensitive to which `python`, `mpicc`
  and `mpifort` come first on `PATH`. If a build fails oddly, print
  `which python fypp mpicc mpifort` and `mpifort --version` before anything
  else.
- **A fresh `~/Work/ecland_venv` per attempt** is cheaper than debugging a
  contaminated environment.
- **Homebrew changes.** A `brew upgrade` of `open-mpi` or `gcc` can invalidate
  an existing build tree; rebuild from a clean tree rather than patching it.
- **Test outcomes vary.** Which tests pass can depend on the ecLand revision,
  compiler version and macOS version. Record the revision
  (`git -C ~/Work/ecland rev-parse HEAD`) and the compiler versions with any
  result you report.
- **Inspecting output.** ecLand4U provides a `landgram.py` diagnostic for
  looking at test output at a site; see that repository for usage.

## Where this fits

A successful build and `ctest -L ecland` is **Level 0** of the benchmark
cascade in [07 — ecLand benchmark cascade](07-ecland-benchmark-cascade.md).
Passing it says the code builds and its own tests behave; it says nothing yet
about scientific skill.

Next: [04 — Local LLM with Ollama](04-local-llm-with-ollama.md).
