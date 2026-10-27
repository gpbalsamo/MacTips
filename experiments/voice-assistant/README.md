# Experimental local voice assistant (Ubuntu / WSL2)

Isolated conversational prototype; it has no tools, shell execution, retrieval,
scientific validation, or connection to the MacTips agent architecture.

```
Enter to record -> local faster-whisper -> local Ollama -> local Piper -> speakers
```

Press Enter to start, speak, then press Enter to stop. This terminal-controlled
push-to-talk toggle needs no global keyboard hooks or elevated permissions.
There is no wake word or background listening. Capture stops after 30 seconds
by default, but the terminal still waits for Enter before continuing. Ctrl-C
or terminal EOF exits. Each turn is independent, with no conversation history.
Audio and transcripts stay in memory; the application writes no recordings or
conversation logs. Ollama's own logging is controlled by its administrator.

## Components and resource choices

- [faster-whisper](https://github.com/SYSTRAN/faster-whisper): `base.en` on CPU,
  INT8, four threads, greedy decoding. English only initially; keeps VRAM for
  `qwen2.5-coder:7b`. STT runs after recording ends, not incrementally.
- [Piper](https://github.com/OHF-Voice/piper1-gpl): maintained OHF implementation,
  CPU ONNX synthesis. Check Piper's GPL licence and each voice's model card
  before redistribution.
- `sounddevice` / PortAudio: microphone and speaker I/O through the available
  Linux audio devices, including WSLg when PortAudio exposes them.
- Python standard-library HTTP client: streaming Ollama chat. Completed
  sentences/short phrases are synthesised and played in order on a worker while
  generation continues. Models load once per process. No PyTorch/CUDA STT setup.

These are starting resource choices, not measured latency guarantees. Context
is limited to 4096 tokens, and answers to 256 generated tokens. Long responses
can end at that generation limit. Do not use the 27B model with the current
WSL RAM constraint for this first iteration.

## Setup (manual; these commands install or download things)

Nothing is installed automatically. Review these commands and run them yourself
only when you approve their changes. Run from this directory:

```bash
cd experiments/voice-assistant
# System packages: requires your explicit approval / sudo in a real terminal.
sudo apt-get update
sudo apt-get install --no-install-recommends python3-venv libportaudio2 \
  libasound2-plugins pulseaudio-utils
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

Dependency ranges allow updates and are not a reproducible lockfile. Record the
resolved versions with `.venv/bin/python -m pip freeze` when benchmarking.
PyAV is constrained below 19: the tested faster-whisper 1.2.1 decoder is
incompatible with PyAV 19's removal of the `metadata_errors` argument.
The tested compatible version is PyAV 18.1.0.

Provision weights explicitly while online (approximately hundreds of MB total;
actual transfer size varies). These are public model downloads, not cloud
inference. The application never downloads weights or pulls Ollama models:

```bash
mkdir -p models
.venv/bin/python -c 'from huggingface_hub import snapshot_download; snapshot_download("Systran/faster-whisper-base.en", local_dir="models/faster-whisper-base.en")'
cd models
../.venv/bin/python -m piper.download_voices en_US-lessac-medium
cd ..
```

Use an already installed **local** Ollama model, as on the target machine:

```bash
ollama list
ollama ps
```

For strict offline use, disable Ollama cloud features in the server's own
configuration ([`OLLAMA_NO_CLOUD=1`](https://github.com/ollama/ollama/blob/main/docs/faq.mdx),
on versions supporting it) or disconnect
external networking after provisioning. Changing the Ollama service is outside
this prototype's scope. Loopback alone cannot prove that another server process
never contacts the Internet. The client refuses model names containing `cloud`,
uses literal loopback/localhost HTTP endpoints only, ignores HTTP proxy settings,
and refuses redirects. Remote LAN and cloud endpoints are deliberately rejected.
STT runs with offline/local-files-only settings, and Piper requires explicit
local voice files. There is no cloud fallback.

## Run

All relative model paths below are relative to the current working directory.

```bash
# No speech packages, microphone, or speakers required for this smoke test:
python3 voice_assistant.py --text 'Reply with one short greeting.' --no-speak

# Typed prompt -> Ollama -> Piper -> speakers (no STT or microphone):
.venv/bin/python voice_assistant.py --text 'Explain evaporation in one sentence.'

# Enumerate available devices without recording or playing audio:
.venv/bin/python voice_assistant.py --list-devices

# Full push-to-talk loop:
.venv/bin/python voice_assistant.py

# Optional device IDs/names and local model paths:
.venv/bin/python voice_assistant.py --input-device 1 --output-device 3 \
  --stt-model models/faster-whisper-base.en \
  --voice models/en_US-lessac-medium.onnx --max-record-seconds 20

# Override the local server and installed model:
python3 voice_assistant.py --text 'Say hello.' --no-speak \
  --endpoint http://127.0.0.1:11434 --model qwen2.5-coder:7b
```

`VOICE_OLLAMA_ENDPOINT` and `VOICE_OLLAMA_MODEL` supply defaults; flags override
them. `--timeout` is the socket I/O timeout, not a total-turn deadline. Errors
exit 1; invalid arguments exit 2; normal exit / Ctrl-C exits 0. A failed turn
stops rather than retrying or silently switching components. Ctrl-C during
generation or playback may wait for an in-flight worker operation to finish.

Only `message.content` is used. Requests disable thinking and ask for a concise
final answer. The streaming filter discards `<think>` / `<analysis>` blocks,
including split tags, plus incomplete tags and unfinished reasoning blocks.
Separate reasoning fields are never printed or spoken. This is format-based:
an arbitrary model emitting untagged reasoning inside its answer cannot be
reliably recognised. Use the intended non-thinking coding model initially.

## WSL2 audio troubleshooting

No driver installation, PulseAudio server launch, permission change, or system
configuration edit is performed by this prototype.

1. Run `--list-devices`. An empty list, PortAudio load failure, or missing default
   device is an audio setup problem; use the reported error and device IDs.
2. Verify WSLg is present and the existing `PULSE_SERVER` points to its socket
   (commonly `/mnt/wslg/PulseServer`). Do not overwrite an existing setting
   without understanding the local setup. Older/non-WSLg installations may need
   separate user-managed audio configuration.
3. On Windows, check microphone privacy permissions for desktop applications,
   input mute, and default input/output selection. WSLg microphone availability
   depends on the host's configuration.
4. Device enumeration alone does not prove sound flows. Test `--text` with speech
   first, then a brief microphone turn. The program validates mono 16 kHz input
   and the voice's output rate, reports capture overflow/device errors, and
   rejects empty captures or exact digital silence. Very quiet nonzero audio
   still requires human diagnosis; no arbitrary silence threshold is used.

If PortAudio exposes no usable WSLg devices, stop and diagnose that host setup;
the prototype cannot repair the Windows/WSLg audio bridge. No ALSA or PulseAudio
configuration changes should be guessed automatically.

## Safe checks and acceptance

```bash
python3 -m unittest discover -s . -p 'test_*.py' -v
python3 -m py_compile voice_assistant.py test_voice_assistant.py
python3 voice_assistant.py --help
```

The tests use mocked HTTP/audio and require no third-party dependencies. They
check loopback restrictions, redirect/cloud-name refusal, streaming completion
and errors, reasoning filtering across chunk boundaries, phrase boundaries,
actionable audio errors, ordered speech/failure propagation, and audio-free text
mode. They do not validate actual STT accuracy, Piper compatibility with installed
packages/weights, audible playback, microphone routing, GPU residency or latency.

For real acceptance, manually verify: typed prompt produces a visible answer;
typed prompt produces intelligible speech; a short recorded prompt is recognised
and answered audibly; Ctrl-C exits; wrong device/model paths fail clearly. Measure
latency and inspect `ollama ps` during an actual run before making performance
claims. Do not infer scientific correctness from the assistant's answer.

### Checks performed on 2026-10-24

- PASS: 11 dependency-free unit tests, Python compilation, CLI help, and diff
  whitespace checks.
- PASS: live `python3 voice_assistant.py --text 'Reply with exactly: Hello from
  the local assistant.' --no-speak --timeout 30`, using the default installed
  `qwen2.5-coder:7b`, exited 0 and printed `Hello from the local assistant.`
  The execution sandbox required permission for the localhost connection.
- PASS: `--list-devices` with absent audio dependencies exited 1 with the
  documented actionable missing-dependency error.
- NOT TESTED: real device enumeration, microphone capture, STT, Piper synthesis,
  audible playback, full voice loop, offline network isolation, GPU residency,
  and latency. Speech packages and weights were not installed/downloaded.

### Subsequent local checks (2026-10-24 to 2026-10-25)

- PASS: Piper 1.8.0 synthesis and sounddevice 0.5.6 output through WSLg's
  `pulse` device. The complete text → Qwen → Piper → AirPods path ran
  successfully, with audible speech confirmed by the user.
- PASS: faster-whisper 1.2.1 with local `base.en`, CPU INT8, four threads,
  transcribed in-memory Piper speech exactly: "The local speech recognition
  test is working." This synthetic test does not establish real-microphone
  recognition accuracy.
- BLOCKED (resolved 2026-10-27, see below): WSLg `RDPSource` capture returned zero frames in bounded tests.
  Windows did not recognise the AirPods microphone. Microphone-to-answer
  operation remains unverified; speaker playback works independently.
- PASS: all 11 dependency-free tests rerun before committing the prototype.

Packages and model assets were provisioned with user approval after the initial
checks. Models, virtual environments, caches, recordings and local credentials
are excluded from version control; only source, tests and setup documentation
belong in the prototype commit. No Windows/WSL configuration was changed.

### Microphone working with an OBSBOT camera (2026-10-27)

- With an OBSBOT Meet 2 camera microphone on its original firmware, opening the
  WSLg microphone froze the WSL audio server: after at most one successful
  capture, `pactl info` stopped responding and every later capture or playback
  hung until `wsl --shutdown`. This reproduced on WSLg 1.0.73.2 and, after
  `wsl --update` (WSL 3.0.3), on WSLg 1.0.79, with Windows microphone access
  allowed. Windows-side Python capture of the same microphone also failed (MME
  stalled, DirectSound delivered digital silence).
- After an **OBSBOT firmware update**, three consecutive bounded 3 s WSLg
  captures returned real audio (peaks 3,340 to 20,690 of 32,767) and the audio
  server kept responding after each.
- PASS (user-confirmed): the full push-to-talk loop, microphone through
  faster-whisper, Ollama and Piper to speech output.
- Audio device checks and device listing now give up after 15 s with a
  "restart WSL" message instead of hanging if the WSLg audio server is frozen
  (12 dependency-free tests pass).
- If the microphone freezes WSL audio again with another device, check the
  device firmware first. A Windows-side capture bridge was built and then
  removed once the firmware update made it unnecessary.
