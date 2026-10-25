"""Deterministic response validators. Never execute generated code or commands."""
from fractions import Fraction
import json
import math
import re

from .types import Contract, Verification

UNCERTAIN = re.compile(r"\b(i (?:do not|don't|cannot|can't) know|not sure|uncertain|"
                       r"cannot verify|can't verify|might be wrong|insufficient (?:information|evidence))\b", re.I)
DANGEROUS = re.compile(
    r'\brm\s|\bgit\s+(?:reset|clean|push\s+.*--force)|\b(?:sudo|mkfs|dd)\b|'
    r'\b(?:shutdown|reboot|sbatch|qsub)\b|\b(?:curl|wget)\b[^\n]*\|\s*(?:sh|bash)|'
    r'\b(?:chmod|chown)\b|\b(?:Remove-Item|Invoke-Expression)\b', re.I)
UNSUPPORTED = re.compile(r'\b(studies show|research proves|guaranteed|100% accurate|'
                         r'proven safe|all tests pass|i (?:ran|executed|searched|verified))\b', re.I)


def arithmetic(prompt):
    """Only a bounded, single binary operation, using exact rational arithmetic."""
    m = re.fullmatch(r'\s*(?:what is\s+|calculate\s+)?(-?\d{1,9})\s*([+*/-])\s*(-?\d{1,9})\s*[?]?\s*', prompt, re.I)
    if not m:
        return None
    a, op, b = Fraction(m[1]), m[2], Fraction(m[3])
    if op == '/' and b == 0:
        return None
    return {'+': lambda: a + b, '-': lambda: a - b,
            '*': lambda: a * b, '/': lambda: a / b}[op]()


# JSON output is inferred only from an explicit output request, so a question
# *about* JSON ("Explain what JSON is") still gets a plain-text answer.
JSON_REQUEST = re.compile(
    r'\b(?:return|reply|respond|output|give|produce|emit)\b[^.?!\n]{0,40}\bjson\b'
    r'|\bas\s+(?:valid\s+|strict\s+)?json\b|\bjson\s+only\b|\bvalid\s+json\b', re.I)


def infer_contract(prompt, contract=None):
    if contract is not None:
        return contract
    if JSON_REQUEST.search(prompt):
        return Contract(format='json')
    if re.search(r'(?:only|valid|return|write)\s+(?:a\s+)?python (?:code|function|script)', prompt, re.I):
        return Contract(format='python')
    return Contract()


SCHEMA_KEYS = {'type', 'properties', 'required', 'additionalProperties', 'items', 'enum', 'minLength'}
TYPES = {'object': dict, 'array': list, 'string': str, 'number': (int, float),
         'integer': int, 'boolean': bool, 'null': type(None)}


def check_schema_spec(schema):
    """Explicit small JSON Schema subset; unsupported constraints fail closed."""
    if not isinstance(schema, dict) or set(schema) - SCHEMA_KEYS:
        raise ValueError('Unsupported JSON schema keyword')
    if schema.get('type') not in TYPES:
        raise ValueError('Schema needs a supported primitive type')
    allowed = {'type', 'enum'} | {
        'object': {'properties', 'required', 'additionalProperties'},
        'array': {'items'}, 'string': {'minLength'},
    }.get(schema['type'], set())
    if set(schema) - allowed:
        raise ValueError('Schema keyword does not apply to this type')
    if 'properties' in schema:
        if schema['type'] != 'object' or not isinstance(schema['properties'], dict):
            raise ValueError('Invalid schema properties')
        for spec in schema['properties'].values():
            check_schema_spec(spec)
    if 'items' in schema:
        check_schema_spec(schema['items'])
    if 'required' in schema and (not isinstance(schema['required'], list)
                                or any(not isinstance(k, str) for k in schema['required'])):
        raise ValueError('Invalid required fields')
    if 'additionalProperties' in schema and type(schema['additionalProperties']) is not bool:
        raise ValueError('additionalProperties must be boolean')
    if 'minLength' in schema and (type(schema['minLength']) is not int or schema['minLength'] < 0):
        raise ValueError('Invalid minLength')
    if 'enum' in schema and not isinstance(schema['enum'], list):
        raise ValueError('Invalid enum')


def schema_errors(value, schema, path='$'):
    expected = schema['type']
    good = isinstance(value, TYPES[expected])
    if expected in ('integer', 'number') and isinstance(value, bool):
        good = False
    if not good:
        return [f'{path}: wrong type']
    errors = []
    if 'enum' in schema and not any(type(value) is type(v) and value == v for v in schema['enum']):
        errors.append(f'{path}: enum mismatch')
    if isinstance(value, str) and len(value) < schema.get('minLength', 0):
        errors.append(f'{path}: string too short')
    if expected == 'object':
        props = schema.get('properties', {})
        if set(schema.get('required', [])) - set(value):
            errors.append(f'{path}: missing required fields')
        if schema.get('additionalProperties') is False and set(value) - set(props):
            errors.append(f'{path}: extra fields')
        for key in value.keys() & props.keys():
            # Do not echo arbitrary model-generated keys into diagnostics.
            errors.extend(schema_errors(value[key], props[key], path + '.field'))
    if expected == 'array' and 'items' in schema:
        for item in value:
            errors.extend(schema_errors(item, schema['items'], path + '[]'))
    return errors


def strict_json(text):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('duplicate key')
            result[key] = value
        return result
    def invalid(_):
        raise ValueError('nonfinite number')
    def finite_float(text):
        value = float(text)
        if not math.isfinite(value):
            raise ValueError('nonfinite number')
        return value
    return json.loads(text, object_pairs_hook=pairs, parse_constant=invalid, parse_float=finite_float)


def verify(prompt, answer, contract, scientific=False, hooks=()):
    checks, failures = ['nonempty_answer', 'explicit_uncertainty', 'command_safety',
                        'unsupported_claim_markers'], []
    if not answer.strip():
        failures.append('empty_answer')
    if UNCERTAIN.search(answer):
        failures.append('explicit_uncertainty')
    if DANGEROUS.search(answer):
        failures.append('potentially_unsafe_command')
    if UNSUPPORTED.search(answer):
        failures.append('unsupported_claim_marker')
    exact = arithmetic(prompt)
    factual = False
    if exact is not None:
        checks.append('exact_binary_arithmetic')
        try:
            scalar = re.fullmatch(r'\s*(?:the answer is\s*)?(-?\d+(?:\.\d+)?(?:/\d+)?)\s*[.]?\s*', answer, re.I)
            factual = scalar is not None and Fraction(scalar[1]) == exact
        except (ValueError, ZeroDivisionError):
            factual = False
        if not factual:
            failures.append('arithmetic_mismatch')
    if contract.format == 'json':
        checks.append('strict_json')
        try:
            value = strict_json(answer)
            if contract.schema is not None:
                checks.append('json_schema_subset')
                failures.extend(schema_errors(value, contract.schema))
        except (ValueError, TypeError):
            failures.append('invalid_json')
    elif contract.format == 'python':
        checks.append('python_compile_without_execution')
        code = answer
        fenced = re.fullmatch(r'\s*```(?:python)?\s*\n(.*?)\n```\s*', code, re.S)
        if fenced:
            code = fenced[1]
        try:
            compile(code, '<jev-candidate>', 'exec')
        except (SyntaxError, ValueError, OverflowError):
            failures.append('invalid_python_syntax')
    elif contract.format == 'shell':
        # Safety lint only: never invoke a shell to parse/execute model text.
        checks.append('shell_safety_lint_only')
    for index, required in enumerate(contract.required):
        checks.append(f'required_text_{index}')
        if required.casefold() not in answer.casefold():
            failures.append(f'missing_required_text_{index}')
    for hook in hooks:
        # Trusted application-supplied callbacks, never model-selected tools.
        result = hook(prompt, answer)
        if not isinstance(result, Verification):
            raise ValueError('Validator hook must return Verification')
        checks.extend(result.checks)
        failures.extend(result.failures)
        if result.status != 'PASS':
            failures.append('validator_hook_not_passed')
        factual = factual or (result.status == 'PASS' and result.factuality_verified)
    status = 'FAIL' if failures else 'UNVERIFIED' if scientific and not factual else 'PASS'
    return Verification(status, checks, failures, factual,
                        'Exact arithmetic or trusted tool evidence.' if factual else
                        'Structural checks only; scientific/factual claims are not established.')
