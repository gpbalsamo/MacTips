# Escalation package — example

This is what the local agent should prepare after two failed reasonable
attempts (see [AGENTS.md](../../AGENTS.md) and
[docs/06](../../docs/06-hybrid-scientific-assistant.md)). The content below is
**illustrative and invented**; it does not record a real failure.

**Before sending this to an external service, a human must review it**
([docs/09](../../docs/09-security-and-safe-agent-use.md)): remove anything not
authorised for that service, such as tokens, usernames, hostnames and private
paths.

---

## Requested task

Build ecLand and run `ctest -L ecland` following
docs/03-ecland-on-apple-silicon.md.

## Current repository state

```
branch: master
revision: <short commit hash>
git status: clean (no local modifications)
```

## Commands attempted

1. `./ecland-bundle create` — exit 0
2. `./ecland-bundle build --cmake="Python3_EXECUTABLE=...;FYPP=..."` — exit 2
3. Retried after `which fypp` showed `fypp` was not on PATH; re-activated the
   venv and repeated step 2 — exit 2 again

## First meaningful error

```
<the first error line from the log, not the last>
```

## Relevant log excerpt

```
<10–30 lines around the first error; redact private paths and usernames>
```

## Files inspected

- build/CMakeCache.txt (compiler and Python entries)
- <path to the log file>

## Current hypothesis

<one or two sentences, marked as a hypothesis rather than a conclusion — for
example: the build is picking up a different Python from the one holding fypp>

## Environment

- macOS version, architecture (`uname -m`)
- `mpifort --version` (first line), `cmake --version` (first line)
- Output of `./scripts/check_ecland_build.sh` (paths redacted)

## Request

Diagnose the failure, propose the smallest fix, and say how it should be
validated (which command, what output means PASS).
