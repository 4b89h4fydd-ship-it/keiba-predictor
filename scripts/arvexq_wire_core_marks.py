from pathlib import Path

p = Path('arvexq/domain/legacy_evaluation.py')
s = p.read_text(encoding='utf-8')
old = """def install_evaluation_core(namespace: dict) -> None:\n    code = compile(SOURCE, '<arvexq:evaluation_core>', 'exec')\n    exec(code, namespace, namespace)\n"""
new = """def install_evaluation_core(namespace: dict) -> None:\n    code = compile(SOURCE, '<arvexq:evaluation_core>', 'exec')\n    exec(code, namespace, namespace)\n\n    # Final marks must follow the current ability/record engine. The legacy ranker is\n    # retained only for auxiliary diagnostics and lower-mark context.\n    from arvexq.prediction.final_marks import apply_core_marks\n\n    legacy_rank = namespace.get('_rank_evaluations')\n    if callable(legacy_rank) and not getattr(legacy_rank, '_arvexq_core_marks_wrapped', False):\n        def _rank_evaluations_core_marks(detail):\n            result = legacy_rank(detail)\n            target = result if isinstance(result, dict) else detail\n            return apply_core_marks(target)\n\n        _rank_evaluations_core_marks._arvexq_core_marks_wrapped = True\n        _rank_evaluations_core_marks.__name__ = '_rank_evaluations'\n        namespace['_rank_evaluations'] = _rank_evaluations_core_marks\n"""
if new in s:
    print('core marks already wired')
    raise SystemExit(0)
if old not in s:
    raise SystemExit('install_evaluation_core tail not found; refusing unsafe patch')
p.write_text(s.replace(old, new), encoding='utf-8')
print('wired ability/record final marks')
