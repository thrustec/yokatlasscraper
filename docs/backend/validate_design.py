"""Validate Phase 1 artifacts; never calls an API or modifies a database.

Install validation_requirements.lock.txt in a dedicated validation environment.
Run from any directory: python docs/backend/validate_design.py
"""
from __future__ import annotations

import base64
import hashlib
import json
import re
from decimal import Decimal
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator, FormatChecker
from openapi_spec_validator import validate


def main() -> None:
    root = Path(__file__).resolve().parent
    spec = yaml.safe_load((root / 'openapi.yaml').read_text(encoding='utf-8'))
    validate(spec)
    fixtures = json.loads((root / 'contract_fixtures.json').read_text(encoding='utf-8'))['cases']
    for case in fixtures:
        schema = {'$ref': '#/components/schemas/' + case['schema'], 'components': spec['components']}
        errors = list(Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(case['payload']))
        if bool(errors) == case['valid']:
            raise ValueError(f"Unexpected schema result: {case['name']}")
        if case['name'] == 'response-byte-input':
            response = case['payload']['response']
            body = base64.b64decode(response['body_base64'], validate=True)
            if hashlib.sha256(body).hexdigest() != response['body_sha256']:
                raise ValueError('Response byte hash fixture mismatch')

    ids = set()
    operations = []
    for path, methods in spec['paths'].items():
        for method, op in methods.items():
            if method not in ('get', 'post', 'patch', 'put', 'delete'):
                continue
            identifier = op['operationId']
            if identifier in ids:
                raise ValueError('Duplicate operationId: ' + identifier)
            ids.add(identifier)
            operations.append(op)
            if op['x-implementation-status'] != 'planned' or len(op['x-tests']) != 5:
                raise ValueError('Missing status/acceptance scenarios: ' + identifier)
            if path.startswith(('/internal/', '/ops/')):
                if not op['security'] or not op['x-required-scopes']:
                    raise ValueError('Missing private security: ' + identifier)
                if not {'401', '403'}.issubset(op['responses']):
                    raise ValueError('Missing private denial contract: ' + identifier)
            elif op['security'] != []:
                raise ValueError('Anonymous read contract changed: ' + identifier)
            if method == 'post' and identifier != 'claimJob':
                if not any(p.get('$ref') == '#/components/parameters/Idempotency' for p in op['parameters']):
                    raise ValueError('Missing mutation idempotency: ' + identifier)
            for name in re.findall(r'\{([^}]+)\}', path):
                if not any(p.get('in') == 'path' and p.get('name') == name and p.get('required') for p in op['parameters']):
                    raise ValueError('Missing required path input: ' + identifier)

    vectors = json.loads((root / 'canonical_hash_vectors.json').read_text(encoding='utf-8'))['vectors']
    for vector in vectors:
        original = json.loads(vector['input_json'], parse_float=Decimal, parse_int=Decimal)
        canonical = json.loads(vector['canonical_json'], parse_float=Decimal, parse_int=Decimal)
        if original != canonical:
            raise ValueError('Canonical vector changed numeric/source value')
        if hashlib.sha256(vector['canonical_json'].encode('utf-8')).hexdigest() != vector['canonical_sha256']:
            raise ValueError('Canonical vector expected hash mismatch')

    for doc in root.rglob('*.md'):
        for target in re.findall(r'\[[^\]]*\]\(([^)]+)\)', doc.read_text(encoding='utf-8')):
            if target.startswith(('http://', 'https://', '#')):
                continue
            if not (doc.parent / target.split('#')[0]).resolve().exists():
                raise ValueError(f'Missing relative link: {doc.name}: {target}')

    print(json.dumps({'status': 'passed', 'paths': len(spec['paths']), 'operations': len(operations),
                      'schemas': len(spec['components']['schemas']), 'fixtures': len(fixtures),
                      'canonical_vectors': len(vectors), 'runtime_endpoints_tested': False}, ensure_ascii=False))


if __name__ == '__main__':
    main()
