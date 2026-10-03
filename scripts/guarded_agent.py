#!/usr/bin/env python3
"""Guarded local agent: the validator decides, the model only diagnoses.

The protection is structural, not a rule in a prompt (see the results in
docs/04, "Do rules in the system prompt make models escalate?"):

1. A deterministic validator parses ecLand ctest output and returns PASS or
   FAIL with evidence. On PASS the model is never called.
2. On FAIL the run ALWAYS stops and writes an escalation package for a human.
   The model does not decide whether to escalate.
3. The model may only read: find_files, search, inspect_log, show, inside a
   run directory holding the evidence. No action can write, run commands,
   change tolerances, reference data or commits. Anything the model proposes
   is recorded as a proposal for the human, never executed.

    THE LLM CHOOSES ACTIONS. TOOLS PERFORM ACTIONS. VALIDATORS DECIDE PASS/FAIL.

Usage:
    # validate an existing ctest log (no model, deterministic only)
    python3 scripts/guarded_agent.py --ctest-log build/ctest.log --repo ~/ecland

    # same, plus a local-model diagnosis on FAIL
    python3 scripts/guarded_agent.py --ctest-log build/ctest.log --repo ~/ecland \\
        --model gpt-oss:20b

    # run `ctest -L ecland` in a build directory first (documented local test)
    python3 scripts/guarded_agent.py --build-dir ~/ecland/build --repo ~/ecland \\
        --ctest-regex ecland_test_ --model gpt-oss:20b

Exit status: 0 PASS, 2 FAIL (escalation package written), 1 harness error.
Output goes to --output-dir (default ~/agent_runs/guarded/<timestamp>/).
Standard library only; the model is reached only through local Ollama.
"""

import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
import benchmark_ollama_agent as bench  # noqa: E402  (shared read-only tools)

PASS, FAIL = "PASS", "FAIL"

# The only actions the model is given. All are read-only (see self-test).
ALLOWED_ACTIONS = ("find_files", "search", "inspect_log", "show")

# A proposal mentioning any of these is flagged: it touches what only a
# human may change (AGENTS.md, "Never").
PROTECTED = re.compile(
    r"toleran|control file|control data|reference (data|file|output)|regenerat|"
    r"revert|reset --hard|git reset|git clean|force.?push|delete|rm -rf",
    re.IGNORECASE)

# --------------------------------------------------------------------------
# Validator: deterministic, no model
# --------------------------------------------------------------------------

TEST_LINE = re.compile(
    r"Test\s+#(\d+):\s+(\S+)\s+\.*\s*(\*\*\*)?(Passed|Failed|Timeout|Not Run(?: \(Disabled\))?)")
VAR_START = re.compile(r"Validating (\w+) with relative tolerance ([0-9.eE+-]+)")
VERDICT = re.compile(r"^\s*(FAILED|SUCCESS)\s*$")
FIRST_ERROR = re.compile(r"Unable to find executable|Error|error:|Timeout|FAILED", re.IGNORECASE)


def validate_ctest(text: str) -> dict:
    """Parse ctest output into per-test and per-variable verdicts."""
    tests: Dict[str, str] = {}
    variables: Dict[str, Dict[str, str]] = {}
    current_test: Optional[str] = None
    current_var: Optional[str] = None
    first_error: Optional[Tuple[int, str]] = None
    first_var_fail: Optional[Tuple[int, str]] = None  # preferred: the science evidence
    var_line: Tuple[int, str] = (0, "")
    lines = text.splitlines()
    for n, line in enumerate(lines, 1):
        m = re.search(r"Start\s+\d+:\s+(\S+)", line)
        if m:
            current_test = m.group(1)
        m = TEST_LINE.search(line)
        if m:
            # with --output-on-failure a test's output follows its result line
            tests[m.group(2)] = m.group(4)
            current_test = m.group(2)
        m = VAR_START.search(line)
        if m and current_test:
            current_var = m.group(1)
            var_line = (n, line.strip())
            variables.setdefault(current_test, {})[current_var] = "?"
        m = VERDICT.match(line)
        if m and current_test and current_var:
            variables[current_test][current_var] = m.group(1)
            if m.group(1) == "FAILED" and first_var_fail is None:
                first_var_fail = (var_line[0], "%s: %s -> FAILED" % (current_test, var_line[1]))
            current_var = None
        if first_error is None and FIRST_ERROR.search(line) and "tests passed" not in line:
            first_error = (n, line.strip())
    first_error = first_var_fail or first_error
    failed = sorted(t for t, s in tests.items() if s not in ("Passed", "Not Run (Disabled)"))
    status = PASS if tests and not failed else FAIL
    reason = ("all %d tests passed" % sum(s == "Passed" for s in tests.values())
              if status == PASS else
              "no test results found in the log" if not tests else
              "%d test(s) did not pass: %s" % (len(failed), ", ".join(failed)))
    return {"status": status, "reason": reason, "tests": tests, "variables": variables,
            "failed_tests": failed,
            "first_error": {"line": first_error[0], "text": first_error[1]} if first_error else None}


def excerpt(text: str, line: int, before: int = 2, after: int = 12) -> str:
    lines = text.splitlines()
    lo, hi = max(line - 1 - before, 0), min(line + after, len(lines))
    return "\n".join("%d: %s" % (i + 1, lines[i][:200]) for i in range(lo, hi))

# --------------------------------------------------------------------------
# Deterministic evidence collection (read-only git, no model)
# --------------------------------------------------------------------------


def run(cmd: List[str], cwd: Optional[Path] = None, timeout: int = 60) -> Tuple[int, str]:
    try:
        p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
        return p.returncode, (p.stdout + p.stderr).strip()
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 1, "error: %s" % exc


def repo_state(repo: Optional[Path], base: Optional[str]) -> str:
    if repo is None:
        return "(no --repo given)"
    parts = []
    for label, cmd in [("branch", ["git", "branch", "--show-current"]),
                       ("revision", ["git", "log", "-1", "--format=%h %s"]),
                       ("git status --short", ["git", "status", "--short"]),
                       ("recent commits", ["git", "log", "--oneline", "-5"])]:
        _, out = run(cmd, cwd=repo)
        parts.append("%s:\n%s" % (label, out or "(clean)"))
    if base:
        _, out = run(["git", "diff", "--stat", base, "HEAD"], cwd=repo)
        parts.append("git diff --stat %s HEAD:\n%s" % (base, out))
    return "\n\n".join(parts)

# --------------------------------------------------------------------------
# Model diagnosis: read-only, cannot decide anything
# --------------------------------------------------------------------------

DIAG_SYSTEM = (
    "You are a read-only diagnostic assistant. A deterministic validator has already "
    "decided that the ecLand tests FAILED and that a human will decide what to do. You "
    "cannot change anything. Use the tools to read the evidence in the run directory, then "
    "reply with ONLY one JSON object: {\"first_meaningful_error\": \"...\", "
    "\"hypothesis\": \"one or two sentences, stated as a hypothesis\", "
    "\"files_inspected\": [\"...\"], \"proposed_next_step\": \"a suggestion for the human\"}")


def diagnose(model: str, run_dir: Path, max_steps: int, timeout: int) -> dict:
    task = {"prompt": "The files in the sandbox are the ctest output (ctest_output.txt), the "
                      "validator report (validator_report.json) and the repository state "
                      "(repo_state.txt). Diagnose the failure."}
    saved = bench.SYSTEM
    bench.SYSTEM = DIAG_SYSTEM
    try:
        answer, steps, trace, raw = bench.run_agent(
            model, task, bench.Sandbox(run_dir),
            {"temperature": 0.2, "seed": 1, "num_ctx": 16384}, max_steps, timeout, "fixed")
    finally:
        bench.SYSTEM = saved
    actions = sorted({t.split("(", 1)[0] for t in trace})
    return {"model": model, "answer": answer, "steps": steps, "trace": trace,
            "actions_used": actions,
            "raw_if_unparsed": None if answer else raw[:500]}

# --------------------------------------------------------------------------
# Escalation package
# --------------------------------------------------------------------------


def package(args, verdict: dict, log_text: str, state: str, diag: Optional[dict],
            commands: List[str]) -> str:
    fe = verdict["first_error"]
    var_lines = []
    for t, vs in verdict["variables"].items():
        bad = [v for v, s in vs.items() if s == "FAILED"]
        if bad:
            var_lines.append("- %s: %s FAILED" % (t, ", ".join(bad)))
    a = (diag or {}).get("answer") or {}
    proposal = str(a.get("proposed_next_step", "")).strip()
    flag = ""
    if proposal and PROTECTED.search(proposal):
        flag = ("\n\n> **Protected:** this proposal touches tolerances, reference data, "
                "commits or deletion. Only a human may decide it (AGENTS.md, \"Never\"). "
                "The agent has no action that could carry it out.")
    model_part = ("(no model run: deterministic validation only)" if diag is None else
                  "(model returned no usable answer)" if not a else
                  "%s\n\n*Hypothesis from `%s`, not a conclusion.*" % (
                      a.get("hypothesis", "(none)"), diag["model"]))
    files = sorted(set(map(str, a.get("files_inspected", []) or [])) |
                   {"ctest_output.txt", "validator_report.json", "repo_state.txt"})
    return "\n".join([
        "# Escalation package",
        "",
        "Written by `scripts/guarded_agent.py` on %s. The validator decided FAIL; the "
        "run stopped here for a human decision." % dt.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "",
        "**Review before sending anywhere outside this machine** (docs/09): remove "
        "paths, usernames, hostnames and anything not authorised for that service.",
        "",
        "## Requested task", "", args.task, "",
        "## Validator verdict", "", "**FAIL** — %s" % verdict["reason"], "",
        *(var_lines or ["(no per-variable verdicts in the log)"]), "",
        "## Current repository state", "", "```", state, "```", "",
        "## Commands attempted", "", *["%d. `%s`" % (i + 1, c) for i, c in enumerate(commands)], "",
        "## First meaningful error", "", "```",
        ("line %d: %s" % (fe["line"], fe["text"])) if fe else "(none matched)", "```", "",
        "## Relevant log excerpt", "", "```",
        excerpt(log_text, fe["line"]) if fe else "(no error line found)", "```", "",
        "## Files inspected", "", *["- %s" % f for f in files], "",
        "## Current hypothesis", "", model_part, "",
        "## Proposed next step (for the human; not executed)", "",
        (proposal or "(none)") + flag, "",
        "## Agent actions", "",
        "Allowed: %s (read-only). Used: %s." % (
            ", ".join(ALLOWED_ACTIONS),
            ", ".join((diag or {}).get("actions_used") or ["none"])),
        ""])

# --------------------------------------------------------------------------


def main(argv: List[str]) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--ctest-log", type=Path, help="existing ctest output to validate")
    src.add_argument("--build-dir", type=Path, help="run ctest here (sources ./env.sh)")
    p.add_argument("--ctest-regex", default=None, help="ctest -R filter (default: -L ecland)")
    p.add_argument("--repo", type=Path, help="source repository, for read-only git state")
    p.add_argument("--base", help="commit to diff against, e.g. an upstream base")
    p.add_argument("--model", help="Ollama model for read-only diagnosis on FAIL")
    p.add_argument("--task", default="Build ecLand and run its tests; report PASS/FAIL.")
    p.add_argument("--max-steps", type=int, default=12)
    p.add_argument("--timeout", type=int, default=300)
    p.add_argument("--output-dir", type=Path)
    args = p.parse_args(argv)

    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    out = (args.output_dir or Path("~/agent_runs/guarded").expanduser() / stamp).expanduser()
    out.mkdir(parents=True, exist_ok=True)
    commands: List[str] = []

    if args.build_dir:
        sel = "-R %s" % args.ctest_regex if args.ctest_regex else "-L ecland"
        cmd = ". ./env.sh && ctest %s --output-on-failure" % sel
        commands.append("cd %s && %s" % (args.build_dir, cmd))
        print("running: %s" % commands[-1], flush=True)
        _, log_text = run(["bash", "-c", cmd], cwd=args.build_dir.expanduser(), timeout=7200)
    else:
        log_text = args.ctest_log.expanduser().read_text(errors="replace")
        commands.append("(validated existing log %s)" % args.ctest_log)

    verdict = validate_ctest(log_text)
    (out / "ctest_output.txt").write_text(log_text)
    (out / "validator_report.json").write_text(json.dumps(verdict, indent=2))
    print("validator: %s (%s)" % (verdict["status"], verdict["reason"]))
    if verdict["status"] == PASS:
        print("PASS: no model called, nothing to escalate. Evidence in %s" % out)
        return 0

    state = repo_state(args.repo.expanduser() if args.repo else None, args.base)
    (out / "repo_state.txt").write_text(state)
    diag = None
    if args.model:
        t0 = time.perf_counter()
        diag = diagnose(args.model, out, args.max_steps, args.timeout)
        diag["seconds"] = round(time.perf_counter() - t0, 1)
        (out / "diagnosis.json").write_text(json.dumps(diag, indent=2))
        print("diagnosis by %s in %.0fs, actions: %s" % (
            args.model, diag["seconds"], ", ".join(diag["actions_used"]) or "none"))
    pkg = out / "escalation_package.md"
    pkg.write_text(package(args, verdict, log_text, state, diag, commands))
    print("FAIL: stopped for a human decision. Escalation package: %s" % pkg)
    return 2


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except Exception as exc:  # a harness error is never a silent PASS
        print("harness error: %s: %s" % (type(exc).__name__, exc), file=sys.stderr)
        sys.exit(1)
