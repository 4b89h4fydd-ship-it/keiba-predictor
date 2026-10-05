from __future__ import annotations

import json
from pathlib import Path
from typing import Any

EXPORT_VERSION = "arvexq-mass-model-export-v1"


def export_head_runtime(head: str, model_dir: str | Path, output_dir: str | Path) -> dict[str, Any]:
    """Export one trained CatBoost head to standalone Python plus a feature manifest.

    This runs only in the offline ML environment. Production does not need CatBoost or
    scikit-learn after export. The CatBoost model sees only DictVectorizer-produced
    numeric columns, so no categorical runtime dependency is required by the model.
    """
    from catboost import CatBoost
    import joblib

    model_dir = Path(model_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    metadata_path = model_dir / f"{head}.metadata.json"
    model_path = model_dir / f"{head}.cbm"
    vectorizer_path = model_dir / f"{head}.vectorizer.joblib"
    if not metadata_path.exists() or not model_path.exists() or not vectorizer_path.exists():
        raise FileNotFoundError(f"missing trained artifacts for head={head}")

    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    vectorizer = joblib.load(vectorizer_path)
    feature_names = list(vectorizer.get_feature_names_out())

    model = CatBoost()
    model.load_model(str(model_path))
    python_path = output_dir / f"{head}_standalone.py"
    model.save_model(str(python_path), format="python")

    manifest = {
        "exportVersion": EXPORT_VERSION,
        "head": head,
        "task": metadata.get("task"),
        "label": metadata.get("label"),
        "featureCount": len(feature_names),
        "featureNames": feature_names,
        "pythonModel": python_path.name,
        "sourceMetrics": metadata.get("metrics") or {},
    }
    manifest_path = output_dir / f"{head}.manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest


def export_all_runtimes(model_dir: str | Path, output_dir: str | Path) -> dict[str, Any]:
    heads = ("ability", "win", "value", "danger")
    return {
        "exportVersion": EXPORT_VERSION,
        "heads": {head: export_head_runtime(head, model_dir, output_dir) for head in heads},
    }
