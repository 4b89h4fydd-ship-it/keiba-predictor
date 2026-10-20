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
    # Reviewed #057 unknown-circuit fail-closed scheduler change. Keep the
    # historical migration-baseline.json unmodified; pin ONLY this exact new
    # AST so any unrelated change is still rejected by the 200-box audit.
    active_baseline["_schedule_full_history_harvest"] = "cc628fd584de1a8add4ea8f0bc5512ec76be2089cb07668a381a0af1291de6d1"
    # Reviewed #038 data-core unknown-circuit refusal; retain historical
    # migration-baseline.json and pin only this exact revised function AST.
    active_baseline["_data_core_refresh_race"] = "6604b2d7f06fe4a6b2c6105898c4a9a03745e2a6193c6f1ed0ee7242fb2665b7"
    # Integration-only exact AST pins for authorized existing Stage1/2 fixes
    # ported into Stage3-owned boxes. Historical baseline evidence is retained.
    # These pins validate only source identity, NOT integration or production success.
    active_baseline["_nar_attach_recent_batch"] = "c492095a3ffd0e73d2c6cca02e8677a728042882348a1755a2e685c70b2ab1f4"
    active_baseline["_nar_official_result_fast"] = "913736b04f7c5239c473c470bcef07b22adc61a3326dd615ca360ff266a8b7ac"
    active_baseline["_netkeiba_current_result"] = "abb7c93de8d662dd255f4f71b1ed51955e3e19ae0e48ee3167485cf81d6149bb"
    active_baseline["nar_race_detail"] = "0c2566162fcccd68351b852a7acd153ece3eab55b517650da9c9c8499c2e1c73"
    active_baseline["_apply_enrichment"] = "ae00019965c0da27673cd4e92aa3355825185eb8ee168c63839bbc9c6c4e726d"
    active_baseline["_precompute_detail_metrics"] = "92c155147365710f28aaf73e444f646f7e60d44f3b0b0fbb155a71175f1b0ac6"
    # PR #376: reviewed Obihiro-exclusion changes to seven existing owners.
    # Pin exact CI-observed AST digests; do not edit historical migration baseline.
    active_baseline["_bootstrap_rows_local"] = "680d3f643a5815392006dcc6d65cad18ad67a5fbaaf1e41310b7f6300d23c4a8"
    active_baseline["data_core_refresh"] = "9e9af6bffedec2bdf89dd763efc03a2b99d60c637d406f3a9b11dce0041500d8"
    active_baseline["data_core_refresh_day"] = "93eebd46cccb2a587bb0011207693907d8986d4b7e030dd84fec7ccabd9e099d"
    active_baseline["nar_race_summaries"] = "937f0e01dc6d27ef77db2c87f87b7dac69a567cffc1c80672abdc585765b5957"
    active_baseline["prewarm_track"] = "04de4fc9a58f3965d8e5c8e3f8be9bd013ad20835db78259fac5b1428f91ddf8"
    active_baseline["races"] = "9f7041ce8d831f0150dca2d65cf9e83d37c88097df33283c1562deb1b012544c"
    active_baseline["track_pack"] = "257bb1631de6304a03d4bd109c0c485a28b5cc0f7081b2de7b71c9d42f17d2db"
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
