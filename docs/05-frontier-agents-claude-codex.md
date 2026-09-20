# 05 — Frontier agents: Claude Code and Codex

## Not just a chat window

Claude Code and Codex are **repository-aware coding agents**. You start them
inside a repository; they can read files, search, run commands, edit code and
show you diffs, subject to your approval. That is a different working mode from
pasting snippets into a chat.

This page describes the workflow adopted from the guide *How to use Claude Code
and Codex in ecLand-CaMa-Flood development*. Follow the vendors' documentation
for installation and login; MacTips does not automate authentication.

## Start in the repository

```bash
cd repository
claude
```

or:

```bash
cd repository
codex
```

## First prompt: understand, do not touch

Begin every new repository with a read-only orientation:

```text
Analyse this repository carefully before making any changes.

Explain:
1. purpose
2. architecture
3. build/run procedure
4. tests
5. important configuration

Do not modify anything yet.
```

Read the answer critically. Correct any misunderstanding *now*; it is far
cheaper than correcting a wrong edit later.

## Then work in small, bounded steps

```
show proposed action
        ↓
approve bounded task
        ↓
inspect result
        ↓
git diff
        ↓
test
        ↓
commit
```

- **Ask for a proposal first.** "What would you change, and why?" before "do
  it".
- **Approve one bounded task at a time.** "Fix the failing unit test in
  `tests/foo`" rather than "make it work".
- **Inspect the result.** After every change run:

  ```bash
  git status
  git diff
  git diff --stat
  ```

- **Test.** Run the documented tests yourself or ask the agent to; read the
  output. Do not accept "it should work".
- **Commit** only when you understand the change.

## Where frontier agents fit in MacTips

They are the escalation target of the local agent
([06](06-hybrid-scientific-assistant.md)). Use them for:

- difficult debugging (build failures, numerical problems);
- architecture and design decisions;
- code review;
- **teaching** — a validated frontier solution can become reusable local
  knowledge ([08](08-frontier-assisted-specialisation.md)).

## One model can review another

Work produced by one agent can be reviewed by a different one: ask Claude Code
to review a branch written with Codex, or the reverse. Independent reviewers
tend to catch different mistakes. Give the reviewer the diff and the test
output, and ask for concrete problems rather than general approval. Reviews
are advice; tests and validators remain the arbiter.

## Cautions

- Repository content you expose to an agent may be sent to the provider. Read
  [09 — security](09-security-and-safe-agent-use.md) before pointing one at
  unpublished data, credentials or code you are not authorised to share.
- Do not grant blanket permission to run arbitrary shell commands, especially
  anything destructive, remote or long-running.
- A confident explanation is not evidence. Insist on commands run and output
  seen.
