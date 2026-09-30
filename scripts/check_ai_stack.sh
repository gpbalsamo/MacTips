#!/usr/bin/env bash
# check_ai_stack.sh — read-only check of the local AI tooling.
#
# Reports whether an NVIDIA GPU is visible (Linux / WSL2 nodes), whether
# Ollama is installed and responding, which models are downloaded and loaded,
# and which frontier coding agents are on PATH.
#
# It does NOT log in, authenticate, change accounts, pull models, or start
# services. It only runs `--version`, `nvidia-smi` queries, `ollama list`
# and `ollama ps`.
# Compatible with the bash 3.2 shipped with macOS.
#
# Status meanings:
#   PASS      found / responding
#   MISSING   a required tool was not found
#   WARN      installed but not responding as expected
#   OPTIONAL  an optional tool was not found
#   info      informational only
#
# Exit status: 0 if Ollama is installed, 1 otherwise. The GPU check and
# frontier agents are informational and never affect the exit status.

set -u

FAIL=0

report() {
    printf '%-9s %-10s %s\n' "$1" "$2" "$3"
}

echo "== GPU =="
# On WSL2 nvidia-smi lives in /usr/lib/wsl/lib, which may not be on PATH.
SMI=""
if command -v nvidia-smi >/dev/null 2>&1; then
    SMI=nvidia-smi
elif [ -x /usr/lib/wsl/lib/nvidia-smi ]; then
    SMI=/usr/lib/wsl/lib/nvidia-smi
fi
if [ -n "$SMI" ]; then
    if out=$("$SMI" --query-gpu=name,memory.total,driver_version,compute_cap \
            --format=csv,noheader 2>&1); then
        printf '%s\n' "$out" | while IFS= read -r line; do
            report PASS nvidia "$line"
        done
    else
        report WARN nvidia "nvidia-smi found but failed"
        printf '%s\n' "$out" | head -n 3 | sed 's/^/          /'
    fi
elif [ "$(uname -s)" = Darwin ]; then
    report info gpu "macOS: Apple GPU via Metal (no NVIDIA check)"
else
    report OPTIONAL nvidia "nvidia-smi not found (no NVIDIA GPU, or driver not visible)"
fi
echo

echo "== Local inference: Ollama =="
if command -v ollama >/dev/null 2>&1; then
    report PASS ollama "$(ollama --version 2>&1 | head -n 1)"

    if out=$(ollama list 2>&1); then
        n=$(printf '%s\n' "$out" | tail -n +2 | grep -c .)
        report PASS "list" "$n model(s) downloaded"
        printf '%s\n' "$out" | sed 's/^/          /'
    else
        report WARN "list" "'ollama list' failed (is the Ollama service running?)"
        printf '%s\n' "$out" | head -n 3 | sed 's/^/          /'
    fi

    if out=$(ollama ps 2>&1); then
        n=$(printf '%s\n' "$out" | tail -n +2 | grep -c .)
        report PASS "ps" "$n model(s) currently loaded"
        printf '%s\n' "$out" | sed 's/^/          /'
    else
        report WARN "ps" "'ollama ps' failed (is the Ollama service running?)"
        printf '%s\n' "$out" | head -n 3 | sed 's/^/          /'
    fi
else
    report MISSING ollama "'ollama' not found on PATH (see docs/04-local-llm-with-ollama.md)"
    FAIL=1
fi
echo

echo "== Frontier / other coding agents (optional) =="
for agent in claude codex opencode; do
    if command -v "$agent" >/dev/null 2>&1; then
        report PASS "$agent" "$("$agent" --version 2>&1 | head -n 1)"
    else
        report OPTIONAL "$agent" "not found on PATH"
    fi
done
echo

if [ "$FAIL" -eq 0 ]; then
    echo "Result: Ollama is installed."
else
    echo "Result: Ollama is not installed. Frontier agents may still be usable."
fi
exit "$FAIL"
