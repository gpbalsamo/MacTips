"""Offline standard-library tests: no Ollama server or installed model required."""
from dataclasses import asdict
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from jev.backend import (BackendError, FrontierPlaceholder, NoRedirect, Ollama,
                         base_url, clean_answer, select_models)
from jev.pipeline import Assistant
from jev.types import Action, Contract, Judgement, Verification
from jev.verify import check_schema_spec, verify


def review(**overrides):
    value = {k: asdict(Judgement(confidence=0.9, uncertainty=0.1,
        recommended_action=Action.ACCEPT_LOCAL, reason='Complete low-risk response.'))[k]
        for k in Judgement.schema()['required']}
    value.update(overrides)
    return json.dumps(value)


class Fake:
    def __init__(self, *answers, name='fake'):
        self.name = name
        self.answers = iter(answers)
        self.calls = []

    def generate(self, prompt, system, schema=None):
        self.calls.append((prompt, system, schema))
        answer = next(self.answers)
        if isinstance(answer, Exception):
            raise answer
        return answer


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def run_assistant(self, prompt, fast='A useful answer.', strong='A stronger answer.',
                      critique=None, contract=None, hooks=()):
        self.fast = Fake(fast, name='fast')
        self.strong = Fake(strong, name='strong') if strong is not None else None
        self.critic = Fake(critique or review(), name='critic')
        self.assistant = Assistant(self.fast, self.strong, self.critic, self.tmp.name, hooks)
        return self.assistant.run(prompt, contract)

    def test_trivial_request_accepted_and_verified_without_critic(self):
        result = self.run_assistant('What is 2+2?', fast='4')
        self.assertEqual(result['outcome'], 'ANSWER')
        self.assertEqual(result['judge_result']['recommended_action'], Action.ACCEPT_LOCAL)
        self.assertTrue(result['verification_result']['factuality_verified'])
        self.assertEqual(self.critic.calls, [])
        self.assertEqual(self.strong.calls, [])

    def test_general_request_gets_separate_structured_critique(self):
        result = self.run_assistant('Say hello.')
        self.assertEqual(result['outcome'], 'ANSWER')
        self.assertEqual(len(self.critic.calls), 1)
        self.assertEqual(self.critic.calls[0][2], Judgement.schema())
        self.assertFalse(result['verification_result']['factuality_verified'])

    def test_complex_request_escalates_despite_accepting_critic(self):
        result = self.run_assistant('Explain a distributed architecture.', fast='Short answer.')
        self.assertEqual(result['escalated_model'], 'strong')
        self.assertEqual(result['final_answer'], 'A stronger answer.')
        self.assertEqual(result['judge_result']['recommended_action'], Action.ESCALATE_LOCAL)

    def test_current_and_unavailable_tools_do_not_generate_fabricated_answers(self):
        for prompt in ('What is the latest weather?', 'Run the tests in my repository.'):
            with self.subTest(prompt=prompt):
                result = self.run_assistant(prompt)
                self.assertEqual(result['outcome'], 'REQUIRE_TOOL')
                self.assertEqual(self.fast.calls, [])
                self.assertEqual(self.strong.calls, [])

    def test_failed_verification_escalates_and_checks_fresh_answer(self):
        result = self.run_assistant('Return JSON only.', fast='invalid',
            strong='{"answer": 4}', contract=Contract('json'))
        self.assertEqual(result['initial_verification']['status'], 'FAIL')
        self.assertEqual(result['verification_result']['status'], 'PASS')
        self.assertEqual(result['escalated_model'], 'strong')
        self.assertEqual(result['final_answer'], '{"answer": 4}')

    def test_second_failure_stops_at_frontier_placeholder(self):
        result = self.run_assistant('Return JSON only.', fast='bad', strong='still bad')
        self.assertEqual(result['outcome'], 'ESCALATE_FRONTIER')
        self.assertEqual(result['verification_result']['status'], 'FAIL')
        self.assertIn('No frontier service was contacted', result['final_answer'])
        self.assertEqual(len(self.strong.calls), 1)

    def test_wrong_arithmetic_never_accepted_on_critic_confidence(self):
        result = self.run_assistant('2+2', fast='5', strong='4')
        self.assertEqual(result['final_answer'], '4')
        self.assertIn('failed_validation', result['judge_result']['signals'])

    def test_destructive_external_hpc_requests_are_never_executed(self):
        for prompt in ('Delete my files.', 'Send an email to Alice.', 'Buy a laptop.',
                       'Submit an HPC job.', 'Change WSL configuration.', 'git reset --hard'):
            with self.subTest(prompt=prompt):
                result = self.run_assistant(prompt)
                self.assertEqual(result['outcome'], 'ASK_USER')
                self.assertEqual(self.fast.calls, [])
                self.assertEqual(self.critic.calls, [])
        self.assertFalse(hasattr(self.assistant, 'execute'))

    def test_scientific_text_cannot_pass_as_validated_science(self):
        result = self.run_assistant('Derive the water-budget equations.')
        self.assertEqual(result['outcome'], 'ESCALATE_FRONTIER')
        self.assertEqual(result['verification_result']['status'], 'UNVERIFIED')

    def test_trusted_scientific_validator_hook_can_supply_evidence(self):
        hook = lambda p, a: Verification('PASS', ['trusted_calculation'], factuality_verified=True)
        result = self.run_assistant('Derive a numerical result.', hooks=(hook,))
        self.assertEqual(result['outcome'], 'ANSWER')
        self.assertTrue(result['verification_result']['factuality_verified'])

    def test_uncertainty_or_unsupported_claim_never_passes(self):
        for answer in ("I don't know.", 'Studies show this is guaranteed.'):
            with self.subTest(answer=answer):
                result = self.run_assistant('Explain this.', fast=answer, strong=answer)
                self.assertEqual(result['outcome'], 'ESCALATE_FRONTIER')

    def test_malformed_judge_escalates(self):
        result = self.run_assistant('Say hello.', critique='{"confidence": 1}')
        self.assertEqual(result['escalated_model'], 'strong')
        self.assertIn('malformed_judge_output', result['judge_result']['signals'])

    def test_critic_can_request_tool_user_or_frontier(self):
        for action in (Action.REQUIRE_TOOL, Action.ASK_USER, Action.ESCALATE_FRONTIER):
            with self.subTest(action=action):
                result = self.run_assistant('Explain this.', critique=review(recommended_action=action))
                self.assertEqual(result['outcome'], action.value)
                self.assertEqual(self.strong.calls, [])

    def test_backend_failure_is_logged_and_stops_safely(self):
        result = self.run_assistant('Say hello.', fast=BackendError('secret body'))
        self.assertEqual(result['error'], 'local_backend_failure')
        self.assertEqual(result['outcome'], 'ESCALATE_FRONTIER')

    def test_no_strong_model_is_a_safe_placeholder(self):
        result = self.run_assistant('Explain a complex architecture.', strong=None)
        self.assertEqual(result['outcome'], 'ESCALATE_FRONTIER')

    def test_invalid_empty_schema_stops_before_generation(self):
        result = self.run_assistant('Return JSON.', contract=Contract('json', {}))
        self.assertEqual(result['verification_result']['status'], 'FAIL')
        self.assertEqual(result['error'], 'invalid_contract_or_validator')
        self.assertEqual(self.fast.calls, [])

    def test_provenance_contains_stages_and_never_persists_free_text(self):
        secret = 'opaque secret that no regex could detect'
        result = self.run_assistant(secret, fast=secret, strong=secret,
                                    critique=review(reason=secret))
        path = Path(self.tmp.name) / 'requests.jsonl'
        text = path.read_text()
        self.assertNotIn(secret, text)
        logged = json.loads(text)
        for key in ('request', 'initial_model', 'initial_answer', 'judge_result',
                    'escalation_decision', 'escalated_model', 'verification_result',
                    'final_answer', 'latency_seconds', 'total_latency_seconds'):
            self.assertIn(key, logged)
        self.assertEqual(result['request'], secret)  # Full in-memory provenance.
        self.assertFalse(logged['content_logged'])
        self.assertGreater(logged['total_latency_seconds'], 0)
        self.assertEqual(path.stat().st_mode & 0o777, 0o600)

    def test_json_contract_only_when_json_output_is_requested(self):
        from jev.verify import infer_contract
        # Questions about JSON must stay plain text, or a correct prose answer fails.
        for prompt in ('Explain what JSON is in one sentence.',
                       'What is the difference between JSON and YAML?',
                       'Why does JSON forbid trailing commas?',
                       'How do I format dates in JSON?'):
            self.assertEqual(infer_contract(prompt).format, 'text', prompt)
        # Explicit output requests, including the README examples, still infer JSON.
        for prompt in ('Return only JSON with an answer field containing 4.',
                       'Return only JSON matching the schema.',
                       'Reply in JSON.', 'Give the result as JSON.',
                       'Output a JSON object with a name field.',
                       'Respond with valid JSON only.', 'JSON only, please: list two colours.'):
            self.assertEqual(infer_contract(prompt).format, 'json', prompt)
        result = self.run_assistant('Explain what JSON is in one sentence.',
                                    fast='JSON is a text format for structured data.')
        self.assertEqual(result['outcome'], 'ANSWER')
        self.assertNotIn('invalid_json', result['verification_result']['failures'])

    def test_removal_wording_is_treated_as_destructive(self):
        from jev.judge import deterministic
        for prompt in ('Remove all files in my home directory.', 'Please remove the folder data/.',
                       'rm ~/notes.txt', 'rm *.log', 'rm -r build/', 'rm *', 'rmdir build', 'Format my disk.',
                       'Overwrite the files in output/.'):
            self.assertEqual(deterministic(prompt).recommended_action, Action.ASK_USER, prompt)
        # Ordinary uses of the same words are not actions on the user's files.
        for prompt in ('Remove duplicates from a Python list.', 'How do I format a date in Python?',
                       'Explain the term confirmation bias.', 'What does rm do in Unix?',
                       'Explain the rm command.', 'Remove everything after the comma.',
                       'Remove the first item from my list.'):
            self.assertNotEqual(deterministic(prompt).recommended_action, Action.ASK_USER, prompt)


class ValidationTests(unittest.TestCase):
    def test_json_schema_and_malformed_json(self):
        schema = {'type': 'object', 'properties': {'answer': {'type': 'integer'}},
                  'required': ['answer'], 'additionalProperties': False}
        check_schema_spec(schema)
        contract = Contract('json', schema)
        self.assertEqual(verify('Question', '{"answer":4}', contract).status, 'PASS')
        for answer in ('bad', '{}', '{"answer":true}', '{"answer":4,"extra":0}',
                       '{"answer":4,"answer":5}', '{"answer":NaN}', '{"answer":1e999}'):
            self.assertEqual(verify('Question', answer, contract).status, 'FAIL')
        with self.assertRaises(ValueError):
            check_schema_spec({'type': 'number', 'minimum': 3})

    def test_python_compile_never_executes(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / 'should-not-exist'
            code = f'open({str(target)!r}, "w").write("bad")'
            self.assertEqual(verify('Code', code, Contract('python')).status, 'PASS')
            self.assertFalse(target.exists())
        self.assertEqual(verify('Code', 'def broken(:', Contract('python')).status, 'FAIL')

    def test_required_information_and_command_safety(self):
        self.assertEqual(verify('Explain', 'A sentence.', Contract(required=('missing',))).status, 'FAIL')
        self.assertEqual(verify('Command', 'rm -rf /tmp/data', Contract('shell')).status, 'FAIL')

    def test_judge_schema_strict_types_and_bounds(self):
        for fields in ({'confidence': True}, {'uncertainty': float('nan')},
                       {'complexity': 'enormous'}, {'tool_required': 'false'}):
            with self.assertRaises(ValueError):
                Judgement.parse(json.loads(review(**fields)))


class BackendTests(unittest.TestCase):
    def test_installed_model_selection_prefers_7b_14b(self):
        installed = {k: {} for k in ('qwen2.5-coder:7b', 'qwen2.5-coder:14b', 'qwen3.8:27b')}
        self.assertEqual(select_models(installed),
                         ('qwen2.5-coder:7b', 'qwen2.5-coder:14b', 'qwen2.5-coder:14b'))
        self.assertEqual(select_models(installed, strong='qwen3.8:27b')[1], 'qwen3.8:27b')
        with self.assertRaises(BackendError):
            select_models(installed, strong='not-installed')
        self.assertEqual(select_models({'qwen2.5-coder:7b': {}})[1:], (None, None))

    def test_loopback_proxy_redirect_and_cloud_boundaries(self):
        for url in ('https://localhost', 'http://example.com', 'http://localhost/remote',
                    'http://user:pw@localhost', 'http://0.0.0.0'):
            with self.assertRaises(BackendError):
                base_url(url)
        self.assertEqual(base_url('http://localhost:1234'), 'http://127.0.0.1:1234')
        with self.assertRaises(BackendError):
            NoRedirect().redirect_request(None, None, 302, '', {}, 'https://remote')
        client = Ollama('http://localhost')
        with patch.object(client, 'request', return_value={'remote_host': 'remote'}):
            with self.assertRaises(BackendError):
                client.check_local('alias')

    def test_transport_payload_and_thinking_filtered(self):
        client = Ollama('http://localhost')
        with patch.object(client, 'request', side_effect=[{}, {'done': True,
             'done_reason': 'stop', 'message': {'thinking': 'secret', 'content': '<think>secret</think>4'}}]) as request:
            self.assertEqual(client.chat('local', '2+2', 'answer'), '4')
            payload = request.call_args.args[1]
            self.assertFalse(payload['think'])
            self.assertEqual(payload['keep_alive'], 0)
            self.assertNotIn('tools', payload)
        self.assertEqual(clean_answer('answer<analysis>unfinished'), 'answer')
        self.assertEqual(clean_answer('<think>a<analysis>b</analysis>c</think>answer'), 'answer')
        self.assertEqual(clean_answer('answer<thi'), 'answer')

    def test_frontier_is_inert(self):
        with patch('urllib.request.OpenerDirector.open', side_effect=AssertionError('network called')):
            self.assertIn('No frontier service', FrontierPlaceholder().generate('anything'))


if __name__ == '__main__':
    unittest.main()
