#!/usr/bin/env bash
# bootstrap_mac.sh — check (and optionally install) the Homebrew scientific
# toolchain described in docs/01-mac-scientific-setup.md.
#
# Usage:
#   ./scripts/bootstrap_mac.sh --check     read-only report (the default)
#   ./scripts/bootstrap_mac.sh --install   print the plan, ask, then install
#   ./scripts/bootstrap_mac.sh --help
#
# Safety:
#   * Nothing is installed unless you pass --install AND type "yes" when asked.
#   * The exact commands are printed before you are asked.
#   * sudo is never used. Homebrew itself and the Xcode command-line tools are
#     NOT installed by this script; install them by hand (docs/01).
#   * --install refuses to run on anything but macOS.
#
# Compatible with the bash 3.2 shipped with macOS.

set -u

FORMULAE="git wget cmake ninja open-mpi gcc eccodes hdf5 netcdf netcdf-fortran cdo nco"

usage() {
    sed -n '2,17p' "$0" | sed 's/^# \{0,1\}//'
}

report() {
    printf '%-9s %-16s %s\n' "$1" "$2" "$3"
}

MODE=check
case "${1:-}" in
    ""|--check) MODE=check ;;
    --install)  MODE=install ;;
    -h|--help)  usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage >&2; exit 2 ;;
esac

echo "== Platform =="
os=$(uname -s)
arch=$(uname -m)
report info system "$os $arch"
if [ "$os" = Darwin ]; then
    report info macOS "$(sw_vers -productVersion 2>/dev/null)"
    report info memory_GB "$(( $(sysctl -n hw.memsize) / 1073741824 ))"
    report info cpus "$(sysctl -n hw.ncpu)"
    if [ "$arch" = arm64 ]; then
        report PASS architecture "arm64 (native Apple silicon)"
    else
        report WARN architecture "$arch: Intel or a Rosetta shell; see docs/01"
    fi
    if xcode-select -p >/dev/null 2>&1; then
        report PASS xcode-tools "command-line tools installed"
    else
        report MISSING xcode-tools "run: xcode-select --install"
    fi
else
    report WARN platform "not macOS; this script targets Homebrew on macOS"
fi
echo

echo "== Homebrew =="
HAVE_BREW=0
if command -v brew >/dev/null 2>&1; then
    HAVE_BREW=1
    report PASS brew "$(brew --version 2>/dev/null | head -n 1)"
else
    report MISSING brew "not found; install from https://brew.sh (read the script first)"
fi
echo

echo "== Formulae =="
MISSING_LIST=""
if [ "$HAVE_BREW" -eq 1 ]; then
    installed=$(brew list --formula 2>/dev/null)
    for f in $FORMULAE; do
        if printf '%s\n' "$installed" | grep -Fxq "$f"; then
            report PASS "$f" "installed"
        else
            report MISSING "$f" "not installed"
            MISSING_LIST="$MISSING_LIST $f"
        fi
    done
else
    report info formulae "cannot check without Homebrew"
fi
echo

if [ "$MODE" = check ]; then
    if [ -n "$MISSING_LIST" ]; then
        echo "Missing formulae:$MISSING_LIST"
        echo "To install them, review and re-run with --install (nothing is installed by --check)."
    fi
    exit 0
fi

# ---- --install --------------------------------------------------------------
if [ "$os" != Darwin ]; then
    echo "Refusing to install: not macOS." >&2
    exit 1
fi
if [ "$HAVE_BREW" -ne 1 ]; then
    echo "Refusing to install: Homebrew not found. Install it first (https://brew.sh)." >&2
    exit 1
fi
if [ -z "$MISSING_LIST" ]; then
    echo "Nothing to install: all listed formulae are already present."
    exit 0
fi

echo "== Planned commands (nothing has been run) =="
echo "  brew install$MISSING_LIST"
echo
echo "These download and install packages under $(brew --prefix)."
echo "No sudo is used. Review the list above."
printf 'Type "yes" to run the commands above: '
if [ ! -t 0 ]; then
    echo
    echo "No interactive terminal: aborting without installing." >&2
    exit 1
fi
read -r answer
if [ "$answer" != yes ]; then
    echo "Aborted. Nothing was installed."
    exit 1
fi

# shellcheck disable=SC2086  # word-splitting of the formula list is intended
brew install $MISSING_LIST
status=$?
echo
echo "brew exited with status $status. Re-run with --check to confirm."
exit "$status"
