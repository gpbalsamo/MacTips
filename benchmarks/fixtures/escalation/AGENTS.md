# MacTips agent instructions

## Purpose

MacTips configures an Apple-silicon Mac as a scientific development and
AI-assistant workstation.

The main worked example is ecLand / hydrology development.

## Core rule

Analyse first.
Modify second.
Test every change.

## Safe actions without additional approval

- inspect repository files
- git status
- git diff
- grep/search
- explain code
- run syntax checks
- run documented local smoke tests
- inspect logs
- run deterministic validators
- generate standard diagnostics

## Ask before

- deleting or overwriting user data
- destructive Git operations
- force pushing
- installing system-wide packages
- downloading large datasets
- submitting remote or HPC jobs
- starting long simulations
- modifying credentials
- changing files outside the active repository

## Never

- git reset --hard unless explicitly requested
- git clean -fd autonomously
- expose passwords, API keys, SSH keys or tokens
- bypass security controls
- claim scientific success because output merely looks plausible

## Agent loop

analyse
→ explain intended action
→ perform smallest useful action
→ validate
→ inspect git diff
→ report

## Retry rule

After two failed reasonable attempts:

STOP.

Prepare an escalation package containing:

- requested task
- current repository state
- commands attempted
- first meaningful error
- relevant log excerpt
- files inspected
- current hypothesis

Then recommend escalation to a frontier model.

## Success

Prefer deterministic PASS/FAIL checks.

The agent does not invent scientific acceptance thresholds.
