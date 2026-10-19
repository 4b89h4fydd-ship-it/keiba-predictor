"""The requested 200-box structure must contain real, traceable existing code."""
import ast
import importlib
import json
from pathlib import Path
from unittest.mock import patch

import pytest
from arvexq.components.catalog import all_components, describe, assemble_ui
from arvexq.components.runtime import component_path, composed_app_source, install_component
from scripts.arvexq_components_audit import audit

ROOT=Path(__file__).resolve().parents[1]


def test_all_200_boxes_match_fixed_inventory_and_have_no_unallocated_source():
    report=audit()
    assert report['boxes']==200 and report['errors']==[]
    assert report['appDefinitionsMoved']==228
    assert report['parserModulesMoved']==98
    assert report['uiFragmentsMoved']==116
    assert report['definitionParity']
    assert report['productionCertifiedByThisAudit'] is False


def test_importing_all_boxes_starts_no_network_or_database_work():
    with patch('urllib.request.urlopen',side_effect=AssertionError('network on box import')), \
         patch('sqlite3.connect',side_effect=AssertionError('database on box import')):
        for i in range(1,201):
            assert importlib.import_module(f'arvexq.components.item_{i:03d}').ITEM_ID==i


def test_catalog_is_immutable_from_a_consumer():
    before=describe(1)
    changed=describe(1);changed['existing_sources'].append('invented');changed['name']='changed'
    assert describe(1)==before


@pytest.mark.parametrize('bad',[0,201,-1,True,'1',1.0,None])
def test_invalid_box_identity_is_rejected(bad):
    with pytest.raises(ValueError):component_path(bad)


def test_unowned_definition_cannot_be_installed_by_another_box():
    with pytest.raises(ValueError,match='does not own'):
        install_component(20,'_nar_official_result_fast',{})


def test_reserved_prediction_boxes_do_not_delegate_old_models():
    reserved=[s for s in all_components() if s['prediction_reserved']]
    assert len(reserved)==29
    for s in reserved:
        assert s['owned_definitions']==s['owned_modules']==s['assets']==[]
        assert s.get('owned_scripts', [])==[]
    for circuit in ('jra','nar'):
        for name in ('ability','running_style','pace','probability','marks','tickets'):
            module=importlib.import_module(f'arvexq.v3.prediction.{circuit}.{name}')
            assert module.run(evidence={'horses':[{'winOdds':1.1}]}) is None


def test_ui_assembly_and_original_generated_app_are_exactly_equal():
    assert assemble_ui()==(ROOT/'arvexq/ui/static/app.js').read_text()


def test_no_owned_definition_remains_duplicated_in_composition_root():
    source=ast.parse((ROOT/'app.py').read_text())
    names={n.name for n in source.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef))}
    moved={name for s in all_components() for name in s['owned_definitions']}
    assert names.isdisjoint(moved)
    all_names={n.name for n in ast.parse(composed_app_source()).body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef))}
    assert moved.issubset(all_names)


def test_all_existing_http_routes_keep_methods_names_and_signatures():
    import inspect
    import app
    before=json.loads((ROOT/'arvexq/components/routes-baseline.json').read_text())
    now=[{'path':r.path,'methods':sorted(r.methods or []),'name':r.name,
          'signature':str(inspect.signature(r.endpoint))} for r in app.app.routes]
    assert now==before


def test_structural_audit_detects_foreign_or_missing_owned_assets():
    from arvexq.components.item_196 import audit as audit_module
    specs=all_components()
    specs[57]['assets']=['arvexq/components/item_001/nar_weather.py', 'arvexq/components/item_058/ui/does_not_exist.js']
    with patch.object(audit_module, 'all_components', return_value=specs):
        errors=audit_module.audit()['errors']
    assert any('owned asset belongs outside' in error for error in errors)
    assert any('missing owned asset' in error for error in errors)


def test_jra_field_parser_boxes_are_not_mislabeled_as_nar():
    # IDs 008–020 currently own only existing JRA calendar/card callers.
    # NAR observations remain in their separate providers and boxes.
    for item_id in range(8, 21):
        assert describe(item_id)['circuits'] == ['JRA']


def test_nonreserved_component_cannot_pass_with_only_a_source_reference():
    from arvexq.components.item_196 import audit as audit_module
    specs=all_components()
    # A source path by itself must never count as implementation ownership.
    specs[7]['owned_definitions']=[]
    specs[7]['owned_modules']=[]
    specs[7]['assets']=[]
    with patch.object(audit_module, 'all_components', return_value=specs):
        errors=audit_module.audit()['errors']
    assert any('active component has no owned implementation' in error for error in errors)
