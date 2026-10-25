"""Run with python3 -m jev --prompt 'What is 2+2?' from this experiment."""
import argparse
import json
import os
from pathlib import Path
import sys

from .backend import BackendError, LocalModel, Ollama, default_endpoint, select_models
from .pipeline import Assistant
from .types import Contract


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prompt')
    parser.add_argument('--endpoint', default=default_endpoint())
    parser.add_argument('--fast-model', default=os.getenv('JEV_FAST_MODEL'))
    parser.add_argument('--strong-model', default=os.getenv('JEV_STRONG_MODEL'))
    parser.add_argument('--judge-model', default=os.getenv('JEV_JUDGE_MODEL'))
    parser.add_argument('--list-models', action='store_true')
    parser.add_argument('--format', choices=['text', 'json', 'python', 'shell'])
    parser.add_argument('--schema', type=Path, help='local JSON Schema subset; implies --format json')
    parser.add_argument('--require', action='append', default=[], help='required answer substring; repeatable')
    parser.add_argument('--timeout', type=float, default=60)
    parser.add_argument('--max-tokens', type=int, default=384)
    parser.add_argument('--verbose', '--debug', action='store_true')
    args = parser.parse_args(argv)
    if not args.list_models and args.prompt is None:
        parser.error('--prompt is required unless --list-models is used')
    if not 0 < args.timeout <= 300 or not 1 <= args.max_tokens <= 2048:
        parser.error('timeout must be (0, 300] seconds and max-tokens 1..2048')
    if args.schema and args.format not in (None, 'json'):
        parser.error('--schema requires JSON format')
    try:
        client = Ollama(args.endpoint, args.timeout, args.max_tokens)
        installed = client.models()
        if args.list_models:
            print('\n'.join(sorted(installed)))
            return 0
        fast, strong, critic = select_models(installed, args.fast_model, args.strong_model, args.judge_model)
        schema = json.loads(args.schema.read_text()) if args.schema else None
        contract = None
        if args.format or args.schema or args.require:
            from .verify import infer_contract
            inferred = infer_contract(args.prompt)
            contract = Contract(args.format or ('json' if args.schema else inferred.format), schema, tuple(args.require))
        assistant = Assistant(LocalModel(client, fast, 'fast_local'),
            LocalModel(client, strong, 'strong_local') if strong else None,
            LocalModel(client, critic, 'judge') if critic else None)
        print(f'[LOCAL] {fast}', flush=True)
        result = assistant.run(args.prompt, contract)
        judgement = result['judge_result']
        if judgement:
            action = judgement['recommended_action'].value
            print(f'[JUDGE] {action} confidence={judgement["confidence"]:.2f}')
        if result['escalated_model']:
            print(f'[ESCALATE] {result["escalated_model"]}')
        if result['outcome'] == 'ESCALATE_FRONTIER':
            print('[ESCALATE] frontier_placeholder (no external call)')
        verification = result['verification_result']
        print(f'[VERIFY] {verification["status"]}; factuality_verified={verification["factuality_verified"]}')
        print(f'[FINAL] {result["final_answer"]}')
        if args.verbose:
            # No initial/escalated answers or chain-of-thought in debug output.
            trail = {k: result[k] for k in ('judge_result', 'escalation_decision',
                'initial_verification', 'verification_result', 'error', 'latency_seconds', 'total_latency_seconds')}
            print('[DEBUG] ' + json.dumps(trail, indent=2))
        return 0 if result['outcome'] == 'ANSWER' else 2
    except (BackendError, OSError, ValueError):
        print('ERROR: local model discovery/configuration/logging failed; check endpoint and options.', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
