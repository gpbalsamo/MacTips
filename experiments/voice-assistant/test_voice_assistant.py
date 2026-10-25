"""Dependency-free tests: never contact a model, microphone, or speaker."""
import argparse
import io
import json
import unittest
from unittest.mock import Mock, patch
import urllib.error

import voice_assistant as va


class VoiceTests(unittest.TestCase):
    def test_endpoint_boundary(self):
        for endpoint in ('http://example.com', 'https://localhost',
                         'http://127.0.0.1/other', 'http://user:pw@localhost',
                         'http://localhost?x=1', 'http://localhost:wrong',
                         'http://0.0.0.0', 'http://192.168.0.2'):
            with self.subTest(endpoint=endpoint), self.assertRaises(va.AssistantError):
                va.endpoint_url(endpoint)
        self.assertEqual(va.endpoint_url('http://localhost:1234'),
                         'http://127.0.0.1:1234/api/chat')
        self.assertEqual(va.endpoint_url('http://[::1]:11434/'),
                         'http://[::1]:11434/api/chat')

    def test_reasoning_at_every_chunk_boundary(self):
        source = 'Hello <think>secret <analysis>nested</analysis>hidden</think>world.'
        for split in range(len(source) + 1):
            f = va.AnswerFilter()
            result = f.feed(source[:split]) + f.feed(source[split:]) + f.feed('', final=True)
            self.assertEqual(result, 'Hello world.')
        f = va.AnswerFilter()
        self.assertEqual(''.join(f.feed(c) for c in source), 'Hello world.')

    def test_unclosed_reasoning_and_partial_tags(self):
        for text in ('Answer.<think>secret', 'Answer.<thi', 'Answer.<ANALYSIS>secret'):
            f = va.AnswerFilter()
            self.assertEqual(f.feed(text) + f.feed('', final=True), 'Answer.')

    def stream(self, events):
        data = ''.join(json.dumps(event) + '\n' for event in events).encode()
        opener = Mock()
        opener.open.return_value = io.BytesIO(data)
        return opener

    def test_stream_request_and_reasoning_metadata(self):
        opener = self.stream([
            {'message': {'thinking': 'private reasoning', 'content': '<thi'}},
            {'message': {'content': 'nk>secret</think>Final answer.'}},
            {'done': True}])
        with patch.object(va.urllib.request, 'build_opener', return_value=opener):
            self.assertEqual(''.join(va.ollama_answer('Hi', 'http://localhost', 'local')), 'Final answer.')
        request = opener.open.call_args.args[0]
        body = json.loads(request.data)
        self.assertFalse(body['think'])
        self.assertTrue(body['stream'])
        self.assertEqual(body['options']['num_ctx'], 4096)

    def test_network_and_stream_errors(self):
        for events in ([{'error': 'model missing'}], [{'message': {'content': 'partial'}}]):
            with patch.object(va.urllib.request, 'build_opener', return_value=self.stream(events)):
                with self.assertRaises(va.AssistantError):
                    list(va.ollama_answer('Hi', 'http://localhost', 'local'))
        opener = Mock()
        opener.open.side_effect = urllib.error.URLError('connection refused')
        with patch.object(va.urllib.request, 'build_opener', return_value=opener):
            with self.assertRaisesRegex(va.AssistantError, 'request failed'):
                list(va.ollama_answer('Hi', 'http://localhost', 'local'))

    def test_redirect_and_cloud_model_refused(self):
        with self.assertRaises(va.AssistantError):
            va.NoRedirect().redirect_request(None, None, 302, '', {}, 'https://remote')
        with self.assertRaises(va.AssistantError):
            list(va.ollama_answer('Hi', 'http://localhost', 'model:cloud'))

    def test_sentence_stream_and_length_bound(self):
        self.assertEqual(list(va.sentences(['One', '. Two? ', 'Tail'])), ['One.', 'Two?', 'Tail'])
        long = list(va.sentences(['a' * 1000]))
        self.assertTrue(all(len(s) <= 240 for s in long))
        self.assertEqual(''.join(long), 'a' * 1000)

    def test_audio_error_is_actionable(self):
        sd = Mock()
        sd.check_input_settings.side_effect = RuntimeError('no input')
        with self.assertRaisesRegex(va.AssistantError, '--list-devices'):
            va.check_audio(sd, None, None)
        sd.reset_mock()
        va.check_audio(sd, None, None, microphone=False)
        sd.check_input_settings.assert_not_called()

    def test_text_mode_needs_no_audio_or_speech_dependencies(self):
        with patch.object(va, 'audio_module', side_effect=AssertionError('audio touched')):
            with patch.object(va, 'ollama_answer', return_value=iter(['Only answer.'])):
                with patch('sys.stdout', new_callable=io.StringIO) as output:
                    self.assertEqual(va.main(['--text', 'Hi', '--no-speak']), 0)
                    self.assertEqual(output.getvalue(), 'Only answer.\n')

    def test_empty_audio_device_list_fails_clearly(self):
        sd = Mock()
        sd.query_devices.return_value = []
        with patch.object(va, 'audio_module', return_value=sd):
            with patch('sys.stderr', new_callable=io.StringIO) as output:
                self.assertEqual(va.main(['--list-devices']), 1)
                self.assertIn('No audio devices found', output.getvalue())

    def test_speech_order_and_worker_failure(self):
        args = argparse.Namespace(endpoint='http://localhost', model='local', timeout=3)
        speech = Mock()
        with patch.object(va, 'ollama_answer', return_value=iter(['First. ', 'Second.'])):
            with patch('sys.stdout', new_callable=io.StringIO):
                va.respond('Hi', args, speech)
        self.assertEqual([c.args[0] for c in speech.say.call_args_list], ['First.', 'Second.'])
        speech.say.side_effect = va.AssistantError('speaker failed')
        with patch.object(va, 'ollama_answer', return_value=iter(['First.'])):
            with patch('sys.stdout', new_callable=io.StringIO):
                with self.assertRaisesRegex(va.AssistantError, 'speaker failed'):
                    va.respond('Hi', args, speech)


if __name__ == '__main__':
    unittest.main()
