#!/usr/bin/env bash
# check_science_stack.sh — read-only check of the scientific toolchain.
#
# Prints the version and status of each tool. Installs nothing, changes
# nothing, needs no network. Compatible with the bash 3.2 shipped with macOS.
#
# Status meanings:
#   PASS      tool found (version shown)
#   MISSING   a required tool was not found
#   OPTIONAL  an optional tool was not found
#
# Exit status: 0 if every required tool is present, 1 otherwise.

set -u

FAIL=0

report() {
    printf '%-9s %-12s %s\n' "$1" "$2" "$3"
}

# check <required|optional> <label> <command> [version-args...]
check() {
    kind=$1
    label=$2
    cmd=$3
    shift 3
    if command -v "$cmd" >/dev/null 2>&1; then
        ver=$("$cmd" "$@" 2>&1 | head -n 1)
        report PASS "$label" "${ver:-version unknown}"
    elif [ "$kind" = required ]; then
        report MISSING "$label" "'$cmd' not found on PATH"
        FAIL=1
    else
        report OPTIONAL "$label" "'$cmd' not found on PATH"
    fi
}

echo "== Platform =="
printf '%-9s %-12s %s\n' info uname "$(uname -sm)"
if [ "$(uname -s)" = Darwin ]; then
    printf '%-9s %-12s %s\n' info sw_vers "$(sw_vers -productVersion 2>/dev/null)"
fi
echo

echo "== Required =="
check required git     git --version
check required python3 python3 --version
check required cmake   cmake --version
check required mpicc   mpicc --version
check required mpifort mpifort --version
echo

echo "== ecCodes =="
if command -v codes_info >/dev/null 2>&1; then
    report PASS eccodes "$(codes_info -v 2>&1 | head -n 1)"
elif command -v grib_ls >/dev/null 2>&1; then
    report PASS eccodes "grib_ls found ($(grib_ls -V 2>&1 | head -n 1))"
else
    report MISSING eccodes "neither 'codes_info' nor 'grib_ls' found on PATH"
    FAIL=1
fi
echo

echo "== Optional =="
check optional cdo     cdo --version
if command -v ncdump >/dev/null 2>&1; then
    # ncdump has no --version flag; its usage text carries the library version.
    ver=$(ncdump 2>&1 | grep -i 'library version' | head -n 1)
    report PASS ncdump "${ver:-found (version not reported)}"
else
    report OPTIONAL ncdump "'ncdump' not found on PATH"
fi
check optional ninja   ninja --version
echo

if [ "$FAIL" -eq 0 ]; then
    echo "Result: all required tools present."
else
    echo "Result: one or more required tools are MISSING."
    echo "See docs/01-mac-scientific-setup.md."
fi
exit "$FAIL"
