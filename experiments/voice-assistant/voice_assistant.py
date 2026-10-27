#!/usr/bin/env python3
"""Local, terminal-controlled speech conversation. No tools or cloud fallback."""

import argparse
from concurrent.futures import ThreadPoolExecutor
import io
import ipaddress
import json
import os
from pathlib import Path
import re
import sys
import threading
import urllib.error
import urllib.parse
import urllib.request
import wave

# Libraries must never silently fetch weights at inference time.
os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['HF_HUB_DISABLE_TELEMETRY'] = '1'


class AssistantError(Exception):
    pass


def endpoint_url(endpoint):
    """Accept literal loopback addresses only; avoid DNS and remote endpoints."""
    try:
        parsed = urllib.parse.urlsplit(endpoint)
        host = parsed.hostname
        if host != 'localhost' and not ipaddress.ip_address(host).is_loopback:
            raise ValueError('not loopback')
        if (parsed.scheme != 'http' or parsed.username or parsed.password
                or parsed.path not in ('', '/') or parsed.query or parsed.fragment):
            raise ValueError('invalid base URL')
        port = parsed.port or 11434
        # Resolve localhost ourselves; no DNS or proxy involvement.
        host = '127.0.0.1' if host == 'localhost' else host
        authority = f'[{host}]' if ':' in host else host
        return f'http://{authority}:{port}/api/chat'
    except (ValueError, TypeError) as exc:
        raise AssistantError('Ollama endpoint must be an HTTP loopback base URL, '
                             'e.g. http://127.0.0.1:11434') from exc


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise AssistantError('Ollama redirect refused: local-only operation required')


class AnswerFilter:
    """Hide tagged reasoning, including tags split across streaming chunks.

    Unclosed blocks are discarded. This is a format filter, not a semantic
    guarantee against a model writing untagged reasoning in its answer.
    """
    tags = {'<think>': 1, '</think>': -1,
            '<analysis>': 1, '</analysis>': -1}

    def __init__(self):
        self.pending = ''
        self.depth = 0

    def feed(self, text, final=False):
        self.pending += text
        answer = []
        while self.pending:
            lower = self.pending.lower()
            tag = next((t for t in self.tags if lower.startswith(t)), None)
            if tag:
                self.depth = max(0, self.depth + self.tags[tag])
                self.pending = self.pending[len(tag):]
            elif any(t.startswith(lower) for t in self.tags):
                # Even on EOF, discard a partial tag rather than reveal it.
                if final:
                    self.pending = ''
                break
            else:
                if self.depth == 0:
                    answer.append(self.pending[0])
                self.pending = self.pending[1:]
        return ''.join(answer)


def ollama_answer(prompt, endpoint, model, timeout=120):
    if 'cloud' in model.lower():
        raise AssistantError('Cloud model names are refused; use an installed local model')
    payload = {
        'model': model, 'stream': True, 'think': False,
        'messages': [
            {'role': 'system', 'content': 'You are a concise voice assistant. '
             'Return only the final assistant answer in plain spoken language. '
             'Do not include analysis, internal reasoning, or chain-of-thought. '
             'You cannot execute commands or use tools.'},
            {'role': 'user', 'content': prompt}],
        'options': {'num_ctx': 4096, 'num_predict': 256, 'temperature': 0.3},
    }
    request = urllib.request.Request(endpoint_url(endpoint),
                                     data=json.dumps(payload).encode(),
                                     headers={'Content-Type': 'application/json'})
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    answer_filter = AnswerFilter()
    try:
        with opener.open(request, timeout=timeout) as response:
            for line in response:
                if not line.strip():
                    continue
                chunk = json.loads(line)
                if chunk.get('error'):
                    raise AssistantError(f'Ollama error: {chunk["error"]}')
                # Explicitly ignore message.thinking and all other metadata.
                content = chunk.get('message', {}).get('content', '')
                if not isinstance(content, str):
                    raise AssistantError('Ollama returned non-text content')
                clean = answer_filter.feed(content)
                if clean:
                    yield clean
                if chunk.get('done'):
                    tail = answer_filter.feed('', final=True)
                    if tail:
                        yield tail
                    return
        raise AssistantError('Ollama stream ended before its completion marker')
    except urllib.error.HTTPError as exc:
        raise AssistantError(f'Ollama HTTP {exc.code}; check service and installed '
                             f'model {model!r} (no automatic model pull)') from exc
    except (OSError, ValueError) as exc:
        raise AssistantError(f'Ollama request failed: {exc}') from exc


def sentences(chunks):
    """Emit completed sentences, with bounded phrases for punctuation-free text."""
    pending = ''
    for chunk in chunks:
        pending += chunk
        while pending:
            match = re.search(r'[.!?](?:\s+|$)|\n', pending)
            cut = match.end() if match else 0
            if not cut and len(pending) > 240:
                cut = pending.rfind(' ', 0, 240)
                cut = cut if cut > 0 else 240
            if not cut:
                break
            sentence, pending = pending[:cut].strip(), pending[cut:]
            if sentence:
                yield sentence
    if pending.strip():
        yield pending.strip()


def audio_module():
    try:
        import sounddevice as sd
        return sd
    except (ImportError, OSError) as exc:
        raise AssistantError('Audio unavailable: install the documented sounddevice '
                             'and PortAudio dependencies; check WSLg audio.') from exc


def device_arg(value):
    return int(value) if value and value.isdecimal() else value


AUDIO_CHECK_SECONDS = 15


def call_with_timeout(function, seconds, what):
    """Run a call that can block forever when the WSLg audio server is frozen."""
    result, error = [], []

    def target():
        try:
            result.append(function())
        except Exception as exc:  # re-raised in the caller's thread
            error.append(exc)

    worker = threading.Thread(target=target, daemon=True)
    worker.start()
    worker.join(seconds)
    if worker.is_alive():
        raise AssistantError(f'{what} did not respond within {seconds:g}s; the WSLg audio '
                             'server is probably frozen. Restart WSL from Windows '
                             '(wsl --shutdown) and try again.')
    if error:
        raise error[0]
    return result[0] if result else None


def check_audio(sd, input_device, output_device, microphone=True):
    def check():
        if microphone:
            sd.check_input_settings(device=input_device, channels=1,
                                    dtype='float32', samplerate=16000)
        sd.check_output_settings(device=output_device, channels=1, dtype='int16')
    try:
        call_with_timeout(check, AUDIO_CHECK_SECONDS, 'Audio device check')
    except AssistantError:
        raise
    except Exception as exc:
        raise AssistantError(f'Audio device check failed: {exc}. Run --list-devices, '
                             'select --input-device/--output-device, and check '
                             'Windows microphone permission and WSLg.') from exc


def record(sd, device, max_seconds):
    import numpy as np
    blocks = []
    problems = []
    finished = threading.Event()
    count = 0
    limit = int(16000 * max_seconds)

    def callback(data, frames, timing, status):
        nonlocal count
        if status:
            problems.append(str(status))
        keep = min(frames, limit - count)
        if keep > 0:
            blocks.append(data[:keep, 0].copy())
            count += keep
        if count >= limit:
            finished.set()
            raise sd.CallbackStop

    input('Press Enter to start recording (Ctrl-C to quit). ')
    try:
        with sd.InputStream(device=device, channels=1, samplerate=16000,
                            dtype='float32', callback=callback):
            input(f'Recording: press Enter to stop (capture capped at {max_seconds:g}s). ')
    except Exception as exc:
        raise AssistantError(f'Microphone recording failed: {exc}; check --list-devices '
                             'and Windows microphone permissions.') from exc
    if finished.is_set():
        print('Recording reached the duration cap.', file=sys.stderr)
    if problems:
        raise AssistantError('Audio capture reported: ' + '; '.join(sorted(set(problems))))
    if not blocks:
        raise AssistantError('Microphone returned no audio frames')
    audio = np.concatenate(blocks)
    if not np.any(audio):
        raise AssistantError('Microphone returned digital silence; check mute/device routing')
    return audio


class Speech:
    def __init__(self, sd, voice_path, output_device):
        path = Path(voice_path)
        if not path.is_file() or not Path(str(path) + '.json').is_file():
            raise AssistantError('Piper requires a local .onnx voice and matching '
                                 '.onnx.json file; see README setup')
        from piper import PiperVoice
        self.voice = PiperVoice.load(str(path), use_cuda=False)
        self.sd = sd
        self.device = output_device

    def say(self, text):
        import numpy as np
        buffer = io.BytesIO()
        with wave.open(buffer, 'wb') as wav:
            self.voice.synthesize_wav(text, wav)
        buffer.seek(0)
        with wave.open(buffer, 'rb') as wav:
            if wav.getsampwidth() != 2 or wav.getnchannels() != 1:
                raise AssistantError('Piper produced unsupported audio (expected mono PCM16)')
            rate = wav.getframerate()
            pcm = np.frombuffer(wav.readframes(wav.getnframes()), dtype='<i2')
        try:
            self.sd.check_output_settings(device=self.device, channels=1,
                                          dtype='int16', samplerate=rate)
            self.sd.play(pcm, rate, device=self.device, blocking=True)
        except Exception as exc:
            raise AssistantError(f'Speaker playback failed: {exc}; check --output-device '
                                 'and WSLg speaker routing.') from exc


def respond(prompt, args, speech=None):
    chunks = ollama_answer(prompt, args.endpoint, args.model, args.timeout)
    emitted = False
    # At most one queued phrase in addition to current playback. This overlaps
    # generation and synthesis without an unbounded backlog or reordered speech.
    with ThreadPoolExecutor(max_workers=1) as pool:
        previous = None
        for sentence in sentences(chunks):
            if previous is not None:
                previous.result()
            print(sentence, flush=True)
            emitted = True
            if speech:
                previous = pool.submit(speech.say, sentence)
        if previous is not None:
            previous.result()
    if not emitted:
        raise AssistantError('Ollama returned no assistant answer')


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--text', metavar='PROMPT', help='single typed turn; skips STT and microphone')
    p.add_argument('--no-speak', action='store_true', help='text-only output; requires --text')
    p.add_argument('--endpoint', default=os.getenv('VOICE_OLLAMA_ENDPOINT', 'http://127.0.0.1:11434'))
    p.add_argument('--model', default=os.getenv('VOICE_OLLAMA_MODEL', 'qwen2.5-coder:7b'))
    p.add_argument('--stt-model', default='models/faster-whisper-base.en', help='local CTranslate2 model directory')
    p.add_argument('--voice', default='models/en_US-lessac-medium.onnx')
    p.add_argument('--input-device', type=device_arg)
    p.add_argument('--output-device', type=device_arg)
    p.add_argument('--list-devices', action='store_true')
    p.add_argument('--timeout', type=float, default=120, help='Ollama socket timeout in seconds')
    p.add_argument('--max-record-seconds', type=float, default=30)
    return p


def main(argv=None):
    p = parser()
    args = p.parse_args(argv)
    if args.no_speak and args.text is None:
        p.error('--no-speak requires --text')
    if not 0 < args.max_record_seconds <= 120 or not 0 < args.timeout <= 600:
        p.error('recording limit must be (0, 120] and timeout (0, 600] seconds')
    try:
        endpoint_url(args.endpoint)
        if args.list_devices:
            sd = audio_module()
            try:
                devices = call_with_timeout(sd.query_devices, AUDIO_CHECK_SECONDS,
                                            'Audio device listing')
                if not devices:
                    raise AssistantError('No audio devices found; check WSLg audio routing.')
                print(devices)
            except Exception as exc:
                raise AssistantError(f'Cannot enumerate audio devices: {exc}; check WSLg.') from exc
            return 0
        speech = None
        sd = None
        if not args.no_speak:
            sd = audio_module()
            check_audio(sd, args.input_device, args.output_device, args.text is None)
            speech = Speech(sd, args.voice, args.output_device)
        if args.text is not None:
            if not args.text.strip():
                raise AssistantError('--text prompt must not be empty')
            respond(args.text, args, speech)
            return 0
        if not Path(args.stt_model).is_dir():
            raise AssistantError('STT model directory missing; provision it explicitly as documented')
        from faster_whisper import WhisperModel
        stt = WhisperModel(args.stt_model, device='cpu', compute_type='int8',
                           cpu_threads=4, local_files_only=True)
        while True:
            audio = record(sd, args.input_device, args.max_record_seconds)
            segments, _ = stt.transcribe(audio, language='en', beam_size=1,
                                         condition_on_previous_text=False)
            prompt = ' '.join(segment.text.strip() for segment in segments).strip()
            if not prompt:
                print('No speech recognised; try another turn.', file=sys.stderr)
                continue
            # Transcripts are intentionally not echoed or persisted.
            respond(prompt, args, speech)
    except (KeyboardInterrupt, EOFError):
        print('\nStopped.', file=sys.stderr)
        return 0
    except (AssistantError, ImportError, OSError, RuntimeError, ValueError) as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        return 1
    finally:
        if 'sd' in locals() and sd is not None:
            sd.stop()


if __name__ == '__main__':
    sys.exit(main())
