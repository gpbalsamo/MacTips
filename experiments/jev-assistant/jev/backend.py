"""Loopback-only Ollama adapter. Backends generate text; they cannot act."""
import ipaddress
import json
import os
from typing import Protocol
import urllib.error
import urllib.parse
import urllib.request


class BackendError(Exception):
    pass


class Backend(Protocol):
    name: str

    def generate(self, prompt: str, system: str, schema: dict | None = None) -> str: ...


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise BackendError('Redirect refused; only local Ollama is allowed')


def base_url(endpoint):
    try:
        p = urllib.parse.urlsplit(endpoint)
        host = '127.0.0.1' if p.hostname == 'localhost' else p.hostname
        if (p.scheme != 'http' or not ipaddress.ip_address(host).is_loopback
                or p.username or p.password or p.query or p.fragment or p.path not in ('', '/')):
            raise ValueError()
        authority = f'[{host}]' if ':' in host else host
        return f'http://{authority}:{p.port or 11434}'
    except (ValueError, TypeError):
        raise BackendError('Expected an HTTP loopback Ollama base URL') from None


def clean_answer(text):
    """Remove tagged reasoning; never read the separate thinking field."""
    import re
    # Non-streaming by design: no candidate is displayed before verification.
    answer, depth = [], 0
    for part in re.split(r'(</?(?:think|analysis)>)', text, flags=re.I):
        if re.fullmatch(r'<(?:think|analysis)>', part, re.I):
            depth += 1
        elif re.fullmatch(r'</(?:think|analysis)>', part, re.I):
            depth = max(0, depth - 1)
        elif depth == 0:
            answer.append(part)
    text = ''.join(answer)
    # Hide incomplete trailing reasoning tags too.
    start = text.rfind('<')
    tags = ('<think>', '</think>', '<analysis>', '</analysis>')
    if start >= 0 and any(tag.startswith(text[start:].lower()) for tag in tags):
        text = text[:start]
    return text.strip()


class Ollama:
    def __init__(self, endpoint, timeout=60, max_tokens=384):
        self.base = base_url(endpoint)
        self.timeout = timeout
        self.max_tokens = max_tokens
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())

    def request(self, path, body=None):
        request = urllib.request.Request(self.base + path,
            data=None if body is None else json.dumps(body).encode(),
            headers={'Content-Type': 'application/json'})
        try:
            with self.opener.open(request, timeout=self.timeout) as response:
                data = json.load(response)
            if not isinstance(data, dict) or data.get('error'):
                raise BackendError('Ollama returned an error')
            return data
        except (OSError, ValueError):
            # Do not echo server bodies or prompts into errors/logs.
            raise BackendError('Local Ollama request failed; check service, model and timeout') from None

    def models(self):
        return {m['name']: m for m in self.request('/api/tags').get('models', [])
                if 'cloud' not in m['name'].lower() and not m.get('remote_host')}

    def check_local(self, name):
        if 'cloud' in name.lower():
            raise BackendError('Cloud model refused')
        info = self.request('/api/show', {'model': name})
        if info.get('remote_host') or info.get('remote_model'):
            raise BackendError('Remote-backed model refused')

    def chat(self, name, prompt, system, schema=None):
        self.check_local(name)
        body = {'model': name, 'stream': False, 'think': False,
                'messages': [{'role': 'system', 'content': system},
                             {'role': 'user', 'content': prompt}],
                'options': {'num_ctx': 4096, 'num_predict': self.max_tokens, 'temperature': 0},
                # Unload each response to avoid retaining 7B + 14B together.
                'keep_alive': 0}
        if schema is not None:
            body['format'] = schema
        result = self.request('/api/chat', body)
        if result.get('done') is not True or result.get('done_reason') == 'length':
            raise BackendError('Ollama response incomplete or reached token limit')
        content = result.get('message', {}).get('content')
        if not isinstance(content, str):
            raise BackendError('Ollama response has no text content')
        return clean_answer(content)


class LocalModel:
    def __init__(self, client, name, role):
        self.client, self.name, self.role = client, name, role

    def generate(self, prompt, system, schema=None):
        return self.client.chat(self.name, prompt, system, schema)


class FrontierPlaceholder:
    name = 'frontier_placeholder'

    def generate(self, prompt='', system='', schema=None):
        return ('Frontier escalation would be required. No frontier service was contacted; '
                'a human must review the evidence and choose the next step.')


def select_models(installed, fast=None, strong=None, judge=None):
    """Prefer installed 7B/14B. No automatic fallback to memory-heavy models."""
    def choose(explicit, preferred):
        if explicit:
            if explicit not in installed or 'cloud' in explicit.lower():
                raise BackendError('Requested model is not installed locally')
            return explicit
        return next((m for m in preferred if m in installed), None)
    fast = choose(fast, ['qwen2.5-coder:7b'])
    if fast is None:
        raise BackendError('No default fast model installed; select --fast-model explicitly')
    strong = choose(strong, ['qwen2.5-coder:14b'])
    judge = choose(judge, [strong] if strong else [])
    if strong == fast:
        raise BackendError('Strong model must differ from fast model')
    return fast, strong, judge


def default_endpoint():
    return os.getenv('JEV_OLLAMA_ENDPOINT',
                     os.getenv('VOICE_OLLAMA_ENDPOINT', 'http://127.0.0.1:11434'))
