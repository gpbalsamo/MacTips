"""Small typed contracts; no third-party schema/runtime dependencies."""
from dataclasses import dataclass, field
from enum import Enum
import math


class Action(str, Enum):
    ACCEPT_LOCAL = 'ACCEPT_LOCAL'
    ESCALATE_LOCAL = 'ESCALATE_LOCAL'
    ESCALATE_FRONTIER = 'ESCALATE_FRONTIER'
    REQUIRE_TOOL = 'REQUIRE_TOOL'
    ASK_USER = 'ASK_USER'


@dataclass
class Judgement:
    confidence: float = 0.0
    complexity: str = 'low'
    factuality_risk: str = 'low'
    tool_required: bool = False
    current_information_required: bool = False
    scientific_reasoning_required: bool = False
    coding_reasoning_required: bool = False
    uncertainty: float = 1.0
    recommended_action: Action = Action.ESCALATE_LOCAL
    reason: str = ''
    unsupported_claims: bool = False
    contradictions: bool = False
    signals: list[str] = field(default_factory=list)
    source: str = 'deterministic'

    @classmethod
    def schema(cls):
        properties = {}
        for key in ('confidence', 'uncertainty'):
            properties[key] = {'type': 'number', 'minimum': 0, 'maximum': 1}
        for key in ('complexity', 'factuality_risk'):
            properties[key] = {'type': 'string', 'enum': ['low', 'medium', 'high']}
        for key in ('tool_required', 'current_information_required',
                    'scientific_reasoning_required', 'coding_reasoning_required',
                    'unsupported_claims', 'contradictions'):
            properties[key] = {'type': 'boolean'}
        properties['recommended_action'] = {'type': 'string', 'enum': [a.value for a in Action]}
        properties['reason'] = {'type': 'string', 'minLength': 1}
        return {'type': 'object', 'properties': properties,
                'required': list(properties), 'additionalProperties': False}

    @classmethod
    def parse(cls, data):
        # Strictly reject missing fields, extra fields, bool-as-number and NaN.
        schema = cls.schema()
        if not isinstance(data, dict) or set(data) != set(schema['required']):
            raise ValueError('invalid judge fields')
        for key, spec in schema['properties'].items():
            value = data[key]
            if spec['type'] == 'number':
                if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= 1:
                    raise ValueError('invalid judge score')
            elif spec['type'] == 'boolean' and type(value) is not bool:
                raise ValueError('invalid judge boolean')
            elif spec['type'] == 'string':
                if not isinstance(value, str) or not value.strip():
                    raise ValueError('invalid judge string')
            if 'enum' in spec and value not in spec['enum']:
                raise ValueError('invalid judge enum')
        return cls(**{**data, 'recommended_action': Action(data['recommended_action']),
                      'source': 'local_critic'})


@dataclass
class Contract:
    format: str = 'text'
    schema: dict | None = None
    required: tuple[str, ...] = ()


@dataclass
class Verification:
    status: str
    checks: list[str]
    failures: list[str] = field(default_factory=list)
    factuality_verified: bool = False
    scope: str = 'Structural checks only; no general factual verification.'
