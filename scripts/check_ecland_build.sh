#!/usr/bin/env bash
# check_ecland_build.sh — read-only inspection of an ecLand build tree.
#
# Usage: ./scripts/check_ecland_build.sh [ECLAND_DIR]
#   ECLAND_DIR defaults to $ECLAND_DIR, then ~/Work/ecland.
#
# It checks that the expected build artefacts and environment are in place,
# and lists (without running) the tests labelled "ecland".
#
# IMPORTANT: this script does not build, install or run tests. A PASS here
# means "the build tree looks complete", NOT "ecLand is scientifically
# correct" and NOT "the tests pass". Run
#     cd <ECLAND_DIR>/build && . ./env.sh && ctest -L ecland --output-on-failure
# yourself and read the result (see docs/03-ecland-on-apple-silicon.md).
#
# Compatible with the bash 3.2 shipped with macOS.
# Exit status: 0 if the build tree looks complete, 1 otherwise.

set -u

ECLAND_DIR=${1:-${ECLAND_DIR:-$HOME/Work/ecland}}
FAIL=0

report() {
    printf '%-9s %-32s %s\n' "$1" "$2" "$3"
}

echo "== ecLand tree: $ECLAND_DIR =="

if [ ! -d "$ECLAND_DIR" ]; then
    report MISSING directory "not found; clone https://github.com/ecmwf-ifs/ecland"
    exit 1
fi
report PASS directory "exists"

if git -C "$ECLAND_DIR" rev-parse --git-dir >/dev/null 2>&1; then
    report PASS "git revision" "$(git -C "$ECLAND_DIR" rev-parse --short HEAD 2>/dev/null)"
else
    report OPTIONAL "git revision" "not a git repository"
fi

for f in ecland-bundle build/install.sh build/env.sh; do
    if [ -e "$ECLAND_DIR/$f" ]; then
        report PASS "$f" "present"
    else
        report MISSING "$f" "not found (has the bundle been created and built?)"
        FAIL=1
    fi
done
echo

echo "== Environment (see docs/03) =="
env_check() {
    # env_check <name> <expected value or empty for any-non-empty>
    val=$(printenv "$1" 2>/dev/null || true)
    if [ -n "$2" ] && [ "$val" = "$2" ]; then
        report PASS "$1" "$val"
    elif [ -z "$2" ] && [ -n "$val" ]; then
        report PASS "$1" "$val"
    else
        report WARN "$1" "expected '${2:-<non-empty>}', found '${val:-<unset>}'"
    fi
}
env_check PYTHONNOUSERSITE 1
env_check DR_HOOK_ASSERT_MPI_INITIALIZED 0
env_check CC mpicc
env_check CXX mpicxx
env_check FC mpifort
for t in fypp mpifort cmake ctest; do
    if command -v "$t" >/dev/null 2>&1; then
        report PASS "$t" "$(command -v "$t")"
    else
        report MISSING "$t" "not found on PATH"
        FAIL=1
    fi
done
echo

echo "== Tests labelled 'ecland' (listed only, NOT run) =="
if [ -f "$ECLAND_DIR/build/env.sh" ] && command -v ctest >/dev/null 2>&1; then
    # Subshell: sourcing env.sh must not leak into the caller.
    listing=$( (cd "$ECLAND_DIR/build" && . ./env.sh >/dev/null 2>&1 && ctest -N -L ecland) 2>&1 )
    total=$(printf '%s\n' "$listing" | grep -i 'Total Tests:' | head -n 1)
    report info tests "${total:-could not list tests}"
else
    report WARN tests "skipped (need build/env.sh and ctest)"
fi
echo

if [ "$FAIL" -eq 0 ]; then
    echo "Result: build tree looks complete. Tests were NOT run by this script."
else
    echo "Result: build tree incomplete or environment not ready."
fi
exit "$FAIL"
