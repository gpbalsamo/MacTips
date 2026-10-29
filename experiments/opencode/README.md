# OpenCode on RTXG (experimental)

Termius is the SSH terminal. Work at the Ubuntu shell prompt in `~/MacTips`.
Ollama serves model inference in the background; OpenCode is the coding-agent
interface. The existing JEV CLI is a separate experiment, not automatically
connected to OpenCode. This setup does not install Flint or any model.

## First test: JEV

In Termius after connecting to RTXG:

```bash
cd ~/MacTips/experiments/jev-assistant
python3 -m jev --prompt 'What is 2+2?' --verbose
```

Expected: ACCEPT_LOCAL, verification PASS, final answer `4`. A more expensive
escalation example (uses the already installed 14B model) is:

```bash
python3 -m jev --prompt 'Explain a distributed architecture in two short sentences.' --verbose
```

The latter demonstrates routing; its structural PASS is not factual validation.

## Launch OpenCode

OpenCode 1.19.4 is installed in the ignored `runtime/` directory. Use the wrapper
so the local-only provider, permissions, and repository-local state apply:

```bash
cd ~/MacTips
bash experiments/opencode/run.sh
```

It starts in **Plan** mode with local `qwen2.5-coder:7b`. A first read-only task:

> Read README.md and docs/06-hybrid-scientific-assistant.md. Summarise the local
> assistant architecture in five bullets. Do not edit files or run commands.

All file edits and shell commands require approval; Plan mode adds its own
restrictions. External-directory access, web tools and delegated agents are
denied. Some credential/runtime paths are denied to the read tool. These are
application permissions, not an operating-system sandbox. Review any requested
command against AGENTS.md before approval. Do not use auto-approval flags.

Only the Ollama provider is enabled, both main and auxiliary models are local,
sharing and auto-updates are disabled, and the wrapper disables external plugins
and model-catalog fetching. Runtime session text can be stored locally under
`runtime/data/`; keep credentials out of prompts. This is local inference, not a
complete audit of every network activity of third-party software or Ollama.
No accounts/API keys are needed. Windows/WSL configuration is unchanged.

The configured 8192-token context is a modest initial target for this GPU, not a
large-repository setting or a performance guarantee. Check actual context and
GPU residency with `ollama ps` during use. Keep initial tasks small; do not
increase context or load multiple large models without measuring memory.

## Observed checks

- CLI version, shell syntax, resolved configuration and runtime paths checked.
- Installed Qwen 7B and 14B advertise `completion` and `tools` in Ollama metadata.
- The initial OpenCode 7B smoke test reached local Qwen, but returned raw tool-call
  text instead of the requested greeting. Exit 0 did not establish task success.
  Repository inspection, edits and command execution are not yet validated.
- Do not infer agent reliability from a model advertising tool support.

## Reinstall the pinned CLI if needed

From `~/MacTips`, with Node/npm installed:

```bash
npm install --prefix experiments/opencode/runtime \
  --cache experiments/opencode/runtime/npm-cache \
  --no-audit --no-fund --save-exact opencode-ai@1.19.4
```

The current npm policy separately requires install-script approval. Review
`runtime/node_modules/opencode-ai/postinstall.mjs` before approving that pinned
package with npm's `install-scripts approve` workflow. It selects/links the
native CLI binary and checks its version. Do not bypass npm's approval policy.

Useful checks (no model generation):

```bash
bash experiments/opencode/run.sh --version
bash experiments/opencode/run.sh debug config
bash experiments/opencode/run.sh debug paths
git status --short
```

The wrapper leaves shell profiles and global OpenCode configuration untouched.
It changes directory to this repository before launching. Do not use it to work
on unrelated repositories; they need a separate scoped setup.

Official references: [Ollama integration](https://docs.ollama.com/integrations/opencode),
[OpenCode permissions](https://opencode.ai/docs/permissions/),
[provider configuration](https://opencode.ai/docs/providers/).
