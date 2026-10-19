"""Existing structural audit body owned by #196, without CI side effects."""
from __future__ import annotations
import ast
import hashlib
import json
from collections import Counter
from pathlib import Path

from arvexq.components.catalog import all_components, assemble_ui
from arvexq.components.runtime import composed_app_source

ROOT = Path(__file__).resolve().parents[3]

def audit():
    specs = all_components()
    inventory = json.loads((ROOT / 'docs/independence/requirements.json').read_text())['items']
    errors = []
    owned = {}
    for spec, item in zip(specs, inventory):
        num = spec['id']
        box = ROOT / 'arvexq/components' / f'item_{num:03d}'
        if spec.get('state') != item.get('structural_migration'):
            errors.append(f'{num}: component/ledger structural state mismatch')
        if (num, spec['name']) != (item['id'], item['name']):errors.append(f'{num}: inventory mismatch')
        if not (box / '__init__.py').is_file():errors.append(f'{num}: missing importable box')
        for source in spec['existing_sources']:
            if not (ROOT / source).exists():errors.append(f'{num}: missing source {source}')
        for row in spec['owned_modules']:
            canonical = ROOT / row['canonical']
            if not canonical.is_file():
                errors.append(f'{num}: missing migrated module {row["canonical"]}')
            if box.resolve() not in canonical.resolve().parents:
                errors.append(f'{num}: migrated module belongs outside its responsibility box')
        for asset in spec['assets']:
            canonical = ROOT / asset
            if not canonical.is_file():
                errors.append(f'{num}: missing owned asset {asset}')
            if box.resolve() not in canonical.resolve().parents:
                errors.append(f'{num}: owned asset belongs outside its responsibility box')
        for owned_script in spec.get('owned_scripts', []):
            if not (ROOT / owned_script).is_file():
                errors.append(f'{num}: missing migrated workflow script {owned_script}')
        for name in spec['owned_definitions']:
            if name in owned:errors.append(f'{num}: duplicate definition {name}')
            owned[name]=num
        owned_material = bool(spec['owned_definitions'] or spec['owned_modules'] or spec['assets'] or spec.get('owned_scripts'))
        if spec['prediction_reserved'] and owned_material:
            errors.append(f'{num}: reserved forecast box contains delegated implementation')
        if not spec['prediction_reserved'] and not owned_material:
            errors.append(f'{num}: active component has no owned implementation')
        if spec['state']=='allocated':errors.append(f'{num}: existing source allocation unresolved')
    baseline=json.loads((ROOT / 'arvexq/components/migration-baseline.json').read_text())['definitions']
    reconstructed={n.name:hashlib.sha256(ast.dump(n,include_attributes=False).encode()).hexdigest()
                   for n in ast.parse(composed_app_source()).body
                   if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef))}
    # User-requested removal of the old prediction algorithm: preserve historical
    # baseline evidence on disk, but never require or restore deleted definitions.
    retired_prediction_definitions = ["_learning_probability","_learning_metric","_learning_races","_learning_paired_top1","_v312_method","_v312_base_winner_weights","_winner_learning_profile"]
    active_baseline = {key: value for key, value in baseline.items()
                       if key not in retired_prediction_definitions}
    # Approved removal of the old auto-prediction refresh inside this function.
    # The retained audit-only body has this exact AST hash. All other definitions
    # still have to match the unmodified historical migration baseline.
    active_baseline["_attach_prerace_audit"] = "8e68e6fbbf3582f7929e018304e3f246ae64b55906364afe79fa89df625f0b11"
    parity = reconstructed == active_baseline and not any(
        name in reconstructed for name in retired_prediction_definitions)
    if not parity:
        missing = sorted(set(active_baseline) - set(reconstructed))
        extra = sorted(set(reconstructed) - set(active_baseline))
        changed = sorted(key for key in active_baseline.keys() & reconstructed.keys()
                         if active_baseline[key] != reconstructed[key])
        errors.append(f'app definition parity failed: missing={missing}, extra={extra}, changed={changed}, actual_hashes={[(k,reconstructed[k]) for k in changed]}')

    try:
        if assemble_ui()!=(ROOT/'arvexq/ui/static/app.js').read_text(encoding='utf-8'):
            errors.append('generated UI differs from canonical component assembly')
    except (ValueError,OSError) as exc:errors.append(str(exc))
    return {'boxes':len(specs),'states':dict(Counter(s['state'] for s in specs)),
            'appDefinitionsMoved':len(owned),'parserModulesMoved':sum(len(s['owned_modules']) for s in specs),
            'uiFragmentsMoved':sum(len(s['assets']) for s in specs),
            'definitionParity':parity,'errors':errors,
            'productionCertifiedByThisAudit':False}
