"""One fast attempt, one escalation, independent verification, then stop."""
from dataclasses import asdict
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import time
import uuid

from .backend import BackendError, FrontierPlaceholder
from .judge import deterministic, judge
from .types import Action, Verification
from .verify import check_schema_spec, infer_contract, verify

GENERATOR_SYSTEM = '''Answer the user's request concisely. Return only the final
answer, without analysis or chain-of-thought. Do not claim to have run commands,
accessed files, searched the web, or performed actions. No tools are available.
State missing information rather than invent evidence. For a simple arithmetic
question return only the numeric result. Respect the supplied output contract.'''


def write_log(record, directory):
    """Log useful metadata, never arbitrary user/model text or exception bodies.

    Full provenance is returned in memory to the caller. Free text is deliberately
    withheld on disk rather than pretending regexes can recognise every secret.
    """
    safe = dict(record)
    for field in ('request', 'initial_answer', 'escalated_answer', 'final_answer'):
        if safe.get(field) is not None:
            safe[field] = '[content omitted for privacy]'
    if safe['judge_result'] is not None:
        safe['judge_result'] = {**safe['judge_result'], 'reason': '[decision text omitted for privacy]'}
    # Model aliases are server-supplied free text too. Only fixed known names are
    # logged verbatim; custom aliases are represented by their configured role.
    known = {'qwen2.5-coder:7b', 'qwen2.5-coder:14b', 'qwen3.8:27b',
             'qwen3-coder:30b', 'gpt-oss:20b', 'frontier_placeholder'}
    for field in ('initial_model', 'escalated_model', 'judge_model'):
        if safe.get(field) is not None and safe[field] not in known:
            safe[field] = '[custom model alias omitted]'
    # Hook/critic strings may contain arbitrary text; checks are represented by
    # counts in the persistent log. In-memory provenance keeps detailed evidence.
    for field in ('initial_verification', 'verification_result'):
        if safe.get(field):
            v = safe[field]
            safe[field] = {'status': v['status'], 'check_count': len(v['checks']),
                           'failure_count': len(v['failures']),
                           'factuality_verified': v['factuality_verified']}
    folder = Path(directory)
    folder.mkdir(mode=0o700, parents=True, exist_ok=True)
    path = folder / 'requests.jsonl'
    flags = os.O_APPEND | os.O_CREAT | os.O_WRONLY | getattr(os, 'O_NOFOLLOW', 0)
    fd = os.open(path, flags, 0o600)
    with os.fdopen(fd, 'a', encoding='utf-8') as log:
        log.write(json.dumps(safe, allow_nan=False) + '\n')
    return path


class Assistant:
    """Backend interface is text-only. There is no tool/action executor."""
    def __init__(self, fast_local, strong_local=None, critic=None, log_dir=None, hooks=()):
        self.fast = fast_local
        self.strong = strong_local
        self.critic = critic
        self.frontier = FrontierPlaceholder()
        self.hooks = hooks
        self.log_dir = log_dir or Path(__file__).resolve().parent.parent / 'runtime' / 'logs'

    def run(self, prompt, contract=None):
        started = time.perf_counter()
        record = {'id': uuid.uuid4().hex, 'timestamp': datetime.now(timezone.utc).isoformat(),
                  'request': prompt, 'initial_model': self.fast.name, 'initial_answer': None,
                  'judge_model': self.critic.name if self.critic else None,
                  'judge_result': None, 'escalation_decision': None, 'escalated_model': None,
                  'escalated_answer': None, 'initial_verification': None,
                  'verification_result': None, 'final_answer': None,
                  'outcome': 'UNRESOLVED', 'error': None,
                  'latency_seconds': {stage: 0.0 for stage in (
                      'preflight', 'fast_local', 'judge', 'initial_verify', 'strong_local', 'verify')},
                  'total_latency_seconds': 0.0, 'content_logged': False}

        def timed(stage, function):
            start = time.perf_counter()
            try:
                return function()
            finally:
                record['latency_seconds'][stage] += round(time.perf_counter() - start, 6)

        def blocked(judgement):
            action = judgement.recommended_action
            record['judge_result'] = asdict(judgement)
            record['escalation_decision'] = action.value
            record['verification_result'] = asdict(Verification(
                'UNVERIFIED', ['preflight_policy'], scope='No candidate approved.'))
            if action == Action.ASK_USER:
                record['final_answer'] = 'Human clarification/confirmation is required. No action was executed.'
            else:
                record['final_answer'] = 'A tool or current evidence is required and is unavailable. No action was executed.'
            record['outcome'] = action.value

        try:
            contract = infer_contract(prompt, contract)
            if contract.format not in ('text', 'json', 'python', 'shell'):
                raise ValueError('Unsupported output contract')
            if contract.schema is not None:
                check_schema_spec(contract.schema)
                if contract.format != 'json':
                    raise ValueError('JSON schema requires JSON output format')
            preflight = timed('preflight', lambda: deterministic(prompt))
            if preflight.recommended_action in (Action.ASK_USER, Action.REQUIRE_TOOL):
                blocked(preflight)
            else:
                instruction = GENERATOR_SYSTEM + '\nOutput contract: ' + json.dumps(asdict(contract))
                candidate = timed('fast_local', lambda: self.fast.generate(
                    prompt, instruction, contract.schema))
                record['initial_answer'] = candidate
                initial = timed('initial_verify', lambda: verify(
                    prompt, candidate, contract, preflight.scientific_reasoning_required, self.hooks))
                record['initial_verification'] = asdict(initial)
                decision = timed('judge', lambda: judge(prompt, candidate, self.critic, initial))
                # Verification failure always overrides acceptance, never vice versa.
                if initial.status != 'PASS' and decision.recommended_action == Action.ACCEPT_LOCAL:
                    decision.recommended_action = Action.ESCALATE_LOCAL
                    decision.signals.append('failed_validation')
                    decision.reason = 'Independent verification did not pass.'
                record['judge_result'] = asdict(decision)
                action = decision.recommended_action
                record['escalation_decision'] = action.value
                if action in (Action.ASK_USER, Action.REQUIRE_TOOL):
                    blocked(decision)
                elif action == Action.ACCEPT_LOCAL:
                    # Repeat only if critic identified a new scientific requirement.
                    final_check = initial
                    if decision.scientific_reasoning_required and not preflight.scientific_reasoning_required:
                        final_check = timed('verify', lambda: verify(
                            prompt, candidate, contract, True, self.hooks))
                    record['verification_result'] = asdict(final_check)
                    if final_check.status == 'PASS':
                        record.update(outcome='ANSWER', final_answer=candidate)
                elif action == Action.ESCALATE_LOCAL and self.strong is not None:
                    record['escalated_model'] = self.strong.name
                    # Fresh solution: don't anchor the stronger model to a bad answer.
                    escalated = timed('strong_local', lambda: self.strong.generate(prompt, instruction, contract.schema))
                    record['escalated_answer'] = escalated
                    checked = timed('verify', lambda: verify(prompt, escalated, contract,
                        decision.scientific_reasoning_required, self.hooks))
                    record['verification_result'] = asdict(checked)
                    if checked.status == 'PASS':
                        record.update(outcome='ANSWER', final_answer=escalated)
                if record['final_answer'] is None:
                    record['outcome'] = Action.ESCALATE_FRONTIER.value
                    record['final_answer'] = self.frontier.generate()
                    if record['verification_result'] is None:
                        record['verification_result'] = asdict(Verification(
                            'UNVERIFIED', ['no_approved_local_answer'], scope='No local answer approved.'))
        except BackendError:
            record['error'] = 'local_backend_failure'
            record['outcome'] = Action.ESCALATE_FRONTIER.value
            record['escalation_decision'] = Action.ESCALATE_FRONTIER.value
            record['final_answer'] = self.frontier.generate()
            record['verification_result'] = asdict(Verification('FAIL', ['local_backend'], ['backend_failure']))
        except (ValueError, TypeError):
            record['error'] = 'invalid_contract_or_validator'
            record['final_answer'] = 'The request contract or validator is invalid; no answer was approved.'
            record['verification_result'] = asdict(Verification('FAIL', ['contract'], ['invalid_contract_or_validator']))
        finally:
            record['total_latency_seconds'] = round(time.perf_counter() - started, 6)
            write_log(record, self.log_dir)
        return record
