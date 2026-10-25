# Experimental JEV: Judge → Escalate → Verify

Small, standard-library-only prototype for RTXG; Python 3.10+ is sufficient.
This is a MacTips routing experiment, not the third-party Qualixar Jev product.
It introduces no new dependencies, model downloads, cloud credentials, or paid
API calls. The existing voice assistant and scientific validator remain intact.

```
request → deterministic preflight → fast_local (7B)
    → initial deterministic checks → structured local critic + policy floor
        → ACCEPT_LOCAL → verify → answer
        → ESCALATE_LOCAL → strong_local (14B) → verify → answer or frontier_placeholder
        → ASK_USER / REQUIRE_TOOL → stop and explain the missing requirement
        → ESCALATE_FRONTIER → inert placeholder, no network escalation
```

Verification runs on the first candidate before judging so its failures can
force escalation. If accepted, those same independent checks serve as the final
verification. If the critic introduces a scientific requirement, verification
runs again with that requirement. The stronger model gets a fresh request, not
the possibly incorrect initial answer. There is at most one stronger generation;
an unresolved answer stops for human review. No answer tokens stream to the user
before verification. This sacrifices some voice latency for a clear approval
boundary. Nothing is wired into the voice assistant yet.

## Run

From the repository root:

```bash
cd experiments/jev-assistant
python3 -m jev --list-models
python3 -m jev --prompt 'What is 2+2?'
python3 -m jev --prompt 'Explain a distributed architecture in two short sentences.' --verbose
python3 -m jev --prompt 'What is the latest weather?'
python3 -m jev --prompt 'Delete my files.'
```

The first arithmetic example uses 7B only when exact verification passes. General
requests load 14B for critique; complex ones can load it again for escalation.
Models are explicitly unloaded after each call (`keep_alive: 0`) so the process
does not retain both tiers together on a 16 GB GPU. This trades load latency for
memory headroom. It does not stop models already loaded by other applications.

Sample output:

```text
[LOCAL] qwen2.5-coder:7b
[JUDGE] ACCEPT_LOCAL confidence=1.00
[VERIFY] PASS; factuality_verified=True
[FINAL] 4
```

`[LOCAL]` initially identifies the configured generator; preflight can skip
generation altogether for blocked/tool requests. `--verbose`/`--debug` shows
the structured judgement, verification details, decision and stage timings.
It does not print initial/rejected answers or separate model thinking fields.
`reason` is a short decision summary, not chain-of-thought. Tagged reasoning is
filtered too, but arbitrary untagged model reasoning cannot be reliably detected.

Exit codes: **0** = answer passed the configured checks; **2** = unresolved,
requires a tool/human/frontier review; **1** = discovery/configuration/logging
failure. PASS alone does not mean an answer is factually true.

## Installed-model selection and local-only boundary

Discovery uses Ollama `/api/tags`; names are never assumed to be available.
Defaults, if present: `qwen2.5-coder:7b` for `fast_local`,
`qwen2.5-coder:14b` for `strong_local` and the structured critic. The critic is a
different model from the default generator, but shares its Qwen family and can
share errors. The critic and stronger generator use separate requests; they are
not independent evidence of factual correctness.

No 7B default: require explicit model selection. No 14B default: retain fast
generation but leave the critic/stronger tier unavailable; unresolved work goes
to the placeholder. No automatic fallback loads 20B–30B models. Size/name-based
selection is an operational starting point, not a benchmarked quality ranking.

```bash
python3 -m jev --prompt 'Explain a distributed architecture briefly.' \
  --endpoint http://127.0.0.1:11434 \
  --fast-model qwen2.5-coder:7b --strong-model qwen2.5-coder:14b \
  --judge-model qwen2.5-coder:14b --timeout 60 --max-tokens 384
```

`JEV_OLLAMA_ENDPOINT` overrides the endpoint, falling back to
`VOICE_OLLAMA_ENDPOINT`, then `http://127.0.0.1:11434`, matching the voice
prototype. `JEV_FAST_MODEL`, `JEV_STRONG_MODEL`, `JEV_JUDGE_MODEL` set model
defaults; flags override them. Other installed models can be selected explicitly,
including `qwen3.8:27b`, but their memory/runtime cost requires care. No models
are pulled. The default 4096-token context and 384-token output cap are bounded;
token-limit truncation is treated as a backend failure, not a valid answer.
The socket timeout is not a total-turn deadline.

The client only accepts HTTP loopback URLs, disables proxy use and redirects,
rejects cloud names, and checks `/api/show` for remote-backed model metadata
before generation. It cannot audit the behaviour of the Ollama server itself.
Use a trusted local-only Ollama service; no service configuration is changed here.
The [Ollama API](https://docs.ollama.com/api/chat) supports the JSON/schema response
format used for the critic. No tools are supplied to the model.

## Judge and policy

`Judgement` includes confidence, complexity, factuality risk, tool/current-data
requirements, scientific/coding reasoning flags, uncertainty, recommended action,
reason, unsupported-claim/contradiction flags, signal list and judgement source.
The LLM response must satisfy strict required fields/types/enums/score bounds.

Deterministic policy signals include destructive/external action phrases,
explicit current/web requests, unavailable file/command tools, scientific
reasoning, substantial coding work, complexity/long prompts, uncertainty and
unsupported-claim phrases. They are conservative English-language heuristics,
not a complete intent classifier or factuality detector. Potential action/tool
requests are blocked before generation to avoid pretending they were performed.
Removal/overwrite wording counts only with a file-like object ("remove the
folder data/", `rm notes.txt`, `rm *.log`, `rmdir build`), so "remove duplicates
from a list" or "what does rm do?" are not treated as actions.

Known limitation: a *question* about a destructive command ("What is the
difference between git reset and git revert?") is blocked as `ASK_USER`. This is
deliberate rather than fixed: any useful answer names the command, and the
command-safety lint rejects answers containing it, so letting the question
through would only end at the frontier placeholder after two model loads.
Keyword checks cannot tell "explains `git reset`" from "tells you to run it".

For ordinary answers, the local critic assesses concrete defects: completeness,
unsupported claims, contradictions, complexity and missing evidence, not merely
"are you confident?". It gets the request/candidate as JSON data and a distinct
review system prompt. Prompt injection can still influence a critic; it cannot
override deterministic restrictions or gain any execution capability.

An accepting critic is overridden by high complexity/risk, contradiction or
unsupported-claim flags, explicit uncertainty, confidence below 0.75 or uncertainty
above 0.25. These are **uncalibrated prototype routing settings**, not scientific
acceptance thresholds. Failed independent checks force escalation even when a
critic accepts. Malformed critique also triggers escalation. Exact bounded
binary arithmetic bypasses the LLM critic when independently correct.

## Verification contracts and limits

Every candidate gets nonempty-answer, explicit-uncertainty, command-safety and
unsupported-claim-marker checks. These are lint checks, not proof of safety or
truth. A model's unsupported statement that tests passed is rejected rather than
treated as evidence. No commands, generated programs or proposed actions execute.

Optional contracts:

```bash
python3 -m jev --prompt 'Return only JSON with an answer field containing 4.' --format json
python3 -m jev --prompt 'Return only a Python function that adds two integers.' --format python
python3 -m jev --prompt 'Briefly describe evaporation and condensation.' \
  --require evaporation --require condensation
python3 -m jev --prompt 'Return only JSON matching the schema.' --schema answer.schema.json
```

The last example requires a user-provided local schema file. Supported schema
subset: primitive `type`, object `properties`/`required`/boolean
`additionalProperties`, array `items`, `enum`, string `minLength`. For example:

```json
{"type":"object","properties":{"answer":{"type":"integer"}},"required":["answer"],"additionalProperties":false}
```

Unsupported keywords fail closed. JSON checks reject duplicate keys and nonfinite
numbers. JSON format is inferred only from an explicit output request ("return
only JSON", "reply in JSON", "as JSON", "valid JSON", "JSON only"), not from
merely mentioning JSON, so "Explain what JSON is" gets a plain-text answer.
Explicit code-return phrases can infer Python. Automatic
inference does not recover arbitrary natural-language schemas: use `--schema`
or `--require` for deterministic requirements.

Python is compiled in memory without executing it or producing `.pyc` files.
This proves syntax only, not correctness or safety. Shell mode performs safety
lint only, never shell execution or a claim of full syntax validation. Required
substrings check presence only. Small single binary integer operations use exact
rational arithmetic; they are not a general numerical/scientific calculator.
Duplicate-key checks, arithmetic equality and critic contradiction flags cover
limited consistency cases; there is no general semantic contradiction verifier.

`PASS` means **the listed checks passed**, with a separate
`factuality_verified` flag and scope. Scientific reasoning without independent
calculation/tool evidence remains `UNVERIFIED` even after stronger generation,
and stops at the frontier placeholder. Increasing model size never establishes
a scientific result. Trusted caller-supplied validator hooks accept
`(prompt, answer)` and return `Verification`; model output cannot select or
create these hooks. No scientific tolerances are invented.

## Provenance and privacy

`Assistant.run()` returns an in-memory record with request, initial answer/model,
judge result/model, escalation decision, escalated answer/model, initial/final
verification, final answer, outcome/error, per-stage and total latency. Stages
that were skipped have zero latency and null candidate fields. Total pipeline
latency excludes initial CLI model discovery and disk-log writing.

Every processed request also appends a JSONL metadata record to
`runtime/logs/requests.jsonl`. `runtime/` is ignored. New log files have mode
0600 and directories 0700; symlink log files are refused. Logging failure is an
error rather than silently claiming provenance was saved.

**Raw request/answer/reason text is withheld from disk by default and by design.**
The corresponding fields contain privacy markers; custom model aliases are
masked and validator check details are stored as counts. Decision flags, scores,
outcomes and timings remain observable. This deliberately gives up full-text disk
replay because no regex can reliably identify every secret. The caller retains
full provenance in memory and must not persist it without its own data policy.
There is no unsafe "log everything" switch. Ollama's own server logging is
outside this client's control. This is not a security boundary against a model
encoding sensitive content into scores; do not give the assistant credentials.

## Tests and observed smoke results (2026-10-25)

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s . -p 'test_*.py' -v
# Existing voice regression tests, from repository root:
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover \
  -s experiments/voice-assistant -p 'test_*.py' -v
```

PASS: 25 JEV unit tests and all 11 existing voice regression tests. No syntax or
diff whitespace errors were found; the voice source/test hashes are unchanged.

Offline unit tests mock all model calls. They cover the eight requested core
cases plus strict judge parsing, schema validation, scientific hook behaviour,
uncertainty, model selection, local/remote boundaries and thinking suppression.
They do not measure routing calibration, factual accuracy or voice quality.

Real local Ollama tests on RTXG:

- `What is 2+2?`: 7B → deterministic ACCEPT_LOCAL → PASS → `4`; about 4.35 s
  total with a cold model load, no critic call.
- `Explain a distributed architecture in two short sentences.`: 7B → structured
  14B critic → deterministic complexity escalation → 14B → structural PASS;
  `factuality_verified=False`. About 29.89 s total (4.86 s initial generation,
  16.61 s critic, 8.42 s stronger generation). This is a routing/plumbing smoke
  test, not evidence that 14B is more capable or that its claims are verified.
- `What is the latest weather?`: REQUIRE_TOOL / UNVERIFIED, exit 2, no
  generation. `Send an email to Alice.`: ASK_USER / UNVERIFIED, exit 2, no
  generation and no external action. Both used real local model discovery only.

The memory-heavy 27B/30B routes, paid services, HPC, voice integration and
microphone remain untested and unimplemented here. No packages/models were
installed and no Windows/WSL settings changed for JEV development.

### Update (2026-10-25, after review)

Fixed two pattern defects, with tests (27 JEV tests now pass):

- Any prompt mentioning JSON was forced into JSON output, so a correct prose
  answer to "Explain what JSON is in one sentence." failed as `invalid_json`.
  Live check after the fix: 7B → 14B critic ACCEPT_LOCAL → PASS → plain-text
  answer, exit 0, about 31 s.
- "Remove all files in my home directory." and `rm <path>` without a flag were
  not flagged as destructive. Both are now `ASK_USER`, while "what does rm do?",
  "remove duplicates from a list" and "remove everything after the comma" are
  not.

## Next extension

Add a small set of labelled requests with human-approved contracts and evidence
to evaluate false acceptance/escalation rates. Then connect one deterministic
scientific validator hook before wiring the returned final answer to Piper.
The text-only `Backend` protocol permits future adapters for larger local models,
Codex, ChatGPT or Claude. ECMWF/HPC needs a separate human-confirmed workflow;
no backend may gain action authority simply by returning text. The frontier
placeholder currently makes no network call and never submits work anywhere.
