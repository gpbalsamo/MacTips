# 01 — Scientific setup on an Apple-silicon Mac

This page prepares a modern Mac for compiled scientific software. It uses
[Homebrew](https://brew.sh). The historical MacPorts workflow is **not** part
of this guide; it is preserved only in
[archive/macos-catalina-macports.md](archive/macos-catalina-macports.md).

> **Status:** these are standard, commonly used commands. They have not been
> re-run as part of writing this page. Package names and versions change over
> time; check `brew info <formula>` if something is not found.

## 1. Know your machine

```bash
uname -m                 # arm64 = Apple silicon, x86_64 = Intel (or Rosetta)
sw_vers                  # macOS version
sysctl -n hw.memsize     # unified memory in bytes
sysctl -n hw.ncpu        # logical CPU count
```

To convert memory to GB: `echo $(( $(sysctl -n hw.memsize) / 1024 / 1024 / 1024 )) GB`.

### arm64 versus Intel / Rosetta

- **arm64** is the native architecture of Apple-silicon Macs. Homebrew installs
  under `/opt/homebrew`. Prefer this.
- **x86_64** is Intel. On Apple silicon it runs only through **Rosetta 2**
  translation, and a Rosetta shell installs a *separate* Homebrew under
  `/usr/local`.
- Do not mix the two. Libraries built for one architecture cannot be linked
  into programs built for the other. If `uname -m` prints `x86_64` on an
  Apple-silicon Mac, your terminal is running under Rosetta; fix that first.

## 2. Command-line developer tools

```bash
xcode-select --install
```

This provides `clang`, `make`, `git` and the macOS SDK. Confirm with
`xcode-select -p`.

## 3. Homebrew

Install Homebrew by following the instructions at <https://brew.sh> (read the
script before running it). Then make sure it is on your `PATH`:

```bash
brew --prefix            # expect /opt/homebrew on Apple silicon
brew doctor
```

## 4. Core tools and libraries

```bash
brew install git wget cmake ninja
brew install open-mpi
brew install gcc                 # provides gfortran; needed where a Fortran compiler is required
brew install eccodes
brew install hdf5 netcdf netcdf-fortran
brew install cdo nco
```

| Package | Why |
|---------|-----|
| `git`, `wget` | Source control, downloads |
| `cmake`, `ninja` | Build systems used by ecLand and ECMWF software |
| `open-mpi` | MPI compilers (`mpicc`, `mpicxx`, `mpifort`) and launcher |
| `gcc` | GNU compilers including `gfortran` |
| `eccodes` | GRIB/BUFR encoding and decoding (`grib_ls`, `codes_info`, …) |
| `hdf5`, `netcdf`, `netcdf-fortran` | Scientific file formats and their C / Fortran APIs |
| `cdo`, `nco` | Command-line climate-data operators |

Install only what you need. Each formula pulls dependencies.

## 5. Check the result

```bash
./scripts/check_science_stack.sh
```

The script is read-only. It reports `PASS`, `MISSING` or `OPTIONAL` for each
tool and installs nothing. To see what is missing before installing:

```bash
./scripts/bootstrap_mac.sh --check
```

## 6. Practical notes

- Homebrew's `open-mpi` wraps whichever compiler it was built against.
  `mpifort --version` shows the underlying Fortran compiler; confirm it is what
  you expect before building anything large.
- Keep one MPI implementation per build tree. Mixing MPI stacks is a common
  source of hard-to-diagnose failures.
- Update deliberately (`brew upgrade`), not casually, on a machine you rely on
  for reproducible results. Record versions with `brew list --versions`.

Next: [02 — Python and the science stack](02-python-and-science-stack.md).
