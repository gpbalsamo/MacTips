#!/usr/bin/env python3
"""Skeleton for machine-readable evaluation of a local coding agent.

WHAT THIS IS
    A deliberately small demonstration of the *shape* of an evaluation record
    and of the loop that produces it. Each task yields one JSON object:

        {
          "task": "repository_navigation",
          "model": "example",
          "status": "PASS",
          "runtime_seconds": 12.3,
          "required_escalation": false,
          "notes": ""
        }

WHAT THIS IS NOT
    It does NOT call any language model, and it does NOT measure general
    intelligence or scientific skill. The only built-in task is a deterministic
    stand-in that checks the repository layout, so that the plumbing (task ->
    validator -> JSON record) can be exercised end to end. Its PASS says
    nothing about any model.

WHERE THIS IS GOING
    Real scientific-agent tasks (build diagnosis, running one PLUMBER2 site,
    escalation-package quality, ...) will be added progressively, following
    docs/07-ecland-benchmark-cascade.md and
    docs/08-frontier-assisted-specialisation.md. Each real task must supply a
    deterministic validator; the model never decides PASS/FAIL itself.

Usage:
    python3 scripts/benchmark_local_agent.py
    python3 scripts/benchmark_local_agent.py --model my-model --output results.jsonl

Standard library only; works with the Python 3 shipped on macOS.
"""

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Callable, Dict, List, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent

PASS = "PASS"
FAIL = "FAIL"

# A task returns (status, required_escalation, notes).
TaskResult = Tuple[str, bool, str]


def task_repository_navigation() -> TaskResult:
    """Stand-in task: validate that the key repository files exist.

    A real version would ask the agent "where is X?" and compare its answer with
    this ground truth. Here the "agent" step is omitted on purpose.
    """
    expected = ["README.md", "AGENTS.md", "docs/06-hybrid-scientific-assistant.md"]
    missing = [p for p in expected if not (REPO_ROOT / p).is_file()]
    if missing:
        return FAIL, False, "missing: " + ", ".join(missing)
    return PASS, False, "demo task: no LLM was called; checks repository layout only"


TASKS: Dict[str, Callable[[], TaskResult]] = {
    "repository_navigation": task_repository_navigation,
}


def run_task(name: str, model: str) -> dict:
    """Run one task and return its evaluation record."""
    start = time.perf_counter()
    try:
        status, escalated, notes = TASKS[name]()
    except Exception as exc:  # a crashing task is a FAIL, never a silent PASS
        status, escalated, notes = FAIL, False, "task raised %s: %s" % (type(exc).__name__, exc)
    return {
        "task": name,
        "model": model,
        "status": status,
        "runtime_seconds": round(time.perf_counter() - start, 3),
        "required_escalation": escalated,
        "notes": notes,
    }


def main(argv: List[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--model", default="example", help="label recorded in each result")
    parser.add_argument("--output", help="append results to this JSON-lines file")
    args = parser.parse_args(argv)

    results = [run_task(name, args.model) for name in TASKS]
    for record in results:
        print(json.dumps(record, indent=2))

    if args.output:
        with open(args.output, "a") as fh:
            for record in results:
                fh.write(json.dumps(record) + "\n")

    return 0 if all(r["status"] == PASS for r in results) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
