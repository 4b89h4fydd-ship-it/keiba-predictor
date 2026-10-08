from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from arvexq.prediction.mass_feature_selection import choose_training_manifest, restrict_features
from arvexq.prediction.mass_training_dataset import split_walk_forward

TRAINER_VERSION = "arvexq-mass-model-trainer-v2"


@dataclass(frozen=True)
class HeadSpec:
    name: str
    task: str
    label: str
    include_feature: Callable[[str], bool]
    row_filter: Callable[[dict[str, Any]], bool]


def _ability_feature(name: str) -> bool:
    """Baseline ability excludes current market and current-condition specialization."""
    if name.startswith("market::"):
        return False
    if name.startswith("history::all::"):
        return True
    if name.startswith("relative::history::all::"):
        return True
    if name.startswith("static::age"):
        return True
    if name.startswith("static::body_weight"):
        return True
    return False


def _all_prerace_non_market(name: str) -> bool:
    return not name.startswith("market::")


def _value_feature(name: str) -> bool:
    # Value explicitly needs the market context in addition to racing evidence.
    return True


def _danger_feature(name: str) -> bool:
    return True


def _has_popularity(row: dict[str, Any]) -> bool:
    features = row.get("features") or {}
    try:
        return float(features.get("market::popularity") or 0) > 0
    except (TypeError, ValueError):
        return False


def _top3_popular(row: dict[str, Any]) -> bool:
    features = row.get("features") or {}
    try:
        popularity = float(features.get("market::popularity") or 0)
    except (TypeError, ValueError):
        return False
    return 0 < popularity <= 3


HEAD_SPECS: dict[str, HeadSpec] = {
    "ability": HeadSpec("ability", "binary", "labelWin", _ability_feature, lambda row: True),
    "win": HeadSpec("win", "binary", "labelWin", _all_prerace_non_market, lambda row: True),
    # Research-only calibrated separately, never a synonym for win.
    "podium": HeadSpec("podium", "binary", "labelTop3", _all_prerace_non_market, lambda row: True),
    "value": HeadSpec("value", "regression", "marketResidual", _value_feature, _has_popularity),
    "danger": HeadSpec("danger", "binary", "labelDanger", _danger_feature, _top3_popular),
}

HEAD_FEATURE_LIMITS = {"ability": 5000, "win": 8000, "podium": 8000, "value": 8000, "danger": 6000}


def _target(row: dict[str, Any], spec: HeadSpec) -> float:
    if spec.label in row:
        return float(row[spec.label])
    features = row.get("features") or {}
    finish = float(row.get("finish") or 999)
    popularity = float(features.get("market::popularity") or 0)
    if spec.label == "marketResidual":
        # Positive means the horse finished better than its market rank.
        return popularity - finish
    if spec.label == "labelDanger":
        return float(finish > 3)
    raise KeyError(spec.label)


def _filtered_features(row: dict[str, Any], spec: HeadSpec) -> dict[str, float]:
    features = row.get("features") or {}
    return {
        str(name): float(value)
        for name, value in features.items()
        if spec.include_feature(str(name)) and isinstance(value, (int, float))
    }


def prepare_head_rows(rows: list[dict[str, Any]], head: str) -> list[dict[str, Any]]:
    spec = HEAD_SPECS[head]
    out: list[dict[str, Any]] = []
    for row in rows:
        if not spec.row_filter(row):
            continue
        features = _filtered_features(row, spec)
        if not features:
            continue
        out.append({**row, "modelFeatures": features, "modelTarget": _target(row, spec)})
    return out


def _default_classifier_params() -> dict[str, Any]:
    return {
        "loss_function": "Logloss",
        "eval_metric": "Logloss",
        "iterations": 700,
        "depth": 7,
        "learning_rate": 0.04,
        "l2_leaf_reg": 5.0,
        "random_seed": 20261006,
        "verbose": False,
        "allow_writing_files": False,
    }


def _default_regressor_params() -> dict[str, Any]:
    return {
        "loss_function": "RMSE",
        "eval_metric": "RMSE",
        "iterations": 700,
        "depth": 7,
        "learning_rate": 0.04,
        "l2_leaf_reg": 5.0,
        "random_seed": 20261006,
        "verbose": False,
        "allow_writing_files": False,
    }


def _xy(rows: list[dict[str, Any]], vectorizer: Any | None = None, fit: bool = False):
    from sklearn.feature_extraction import DictVectorizer

    dicts = [row["modelFeatures"] for row in rows]
    if vectorizer is None:
        vectorizer = DictVectorizer(sparse=True)
        fit = True
    x = vectorizer.fit_transform(dicts) if fit else vectorizer.transform(dicts)
    y = [float(row["modelTarget"]) for row in rows]
    return x, y, vectorizer


def _apply_manifest(rows: list[dict[str, Any]], manifest: set[str]) -> list[dict[str, Any]]:
    out=[]
    for row in rows:
        features=restrict_features(row.get("modelFeatures") or {},manifest)
        out.append({**row,"modelFeatures":features})
    return out


def train_head(
    rows: list[dict[str, Any]],
    head: str,
    output_dir: str | Path,
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Train one head using chronological race-group splits and train-only feature pruning."""
    if head not in HEAD_SPECS:
        raise KeyError(f"unknown head: {head}")
    from catboost import CatBoostClassifier, CatBoostRegressor
    import joblib
    from sklearn.metrics import brier_score_loss, log_loss, mean_squared_error, roc_auc_score

    prepared = prepare_head_rows(rows, head)
    split = split_walk_forward(prepared)
    train_rows = split["train"]
    valid_rows = split["valid"]
    test_rows = split["test"]
    if not train_rows or not valid_rows or not test_rows:
        raise ValueError(f"insufficient chronological data for head={head}")

    # Fit the feature manifest on TRAIN only. Validation/test cannot influence which
    # factors survive. This is part of the leakage boundary, not just optimization.
    feature_names = choose_training_manifest(
        train_rows,
        min_coverage=0.01,
        max_features=HEAD_FEATURE_LIMITS[head],
    )
    if not feature_names:
        raise ValueError(f"no usable training features for head={head}")
    manifest=set(feature_names)
    train_rows=_apply_manifest(train_rows,manifest)
    valid_rows=_apply_manifest(valid_rows,manifest)
    test_rows=_apply_manifest(test_rows,manifest)

    x_train, y_train, vectorizer = _xy(train_rows, fit=True)
    x_valid, y_valid, _ = _xy(valid_rows, vectorizer=vectorizer)
    x_test, y_test, _ = _xy(test_rows, vectorizer=vectorizer)

    spec = HEAD_SPECS[head]
    if spec.task == "binary":
        model = CatBoostClassifier(**(_default_classifier_params() | (params or {})))
    else:
        model = CatBoostRegressor(**(_default_regressor_params() | (params or {})))

    model.fit(x_train, y_train, eval_set=(x_valid, y_valid), use_best_model=True)

    metrics: dict[str, Any] = {
        "trainRows": len(train_rows),
        "validRows": len(valid_rows),
        "testRows": len(test_rows),
        "candidateFeatureCount": len(feature_names),
        "vectorizedFeatureCount": len(vectorizer.feature_names_),
    }
    if spec.task == "binary":
        valid_prob = model.predict_proba(x_valid)[:, 1]
        test_prob = model.predict_proba(x_test)[:, 1]
        metrics.update(
            {
                "validLogLoss": float(log_loss(y_valid, valid_prob, labels=[0, 1])),
                "testLogLoss": float(log_loss(y_test, test_prob, labels=[0, 1])),
                "validBrier": float(brier_score_loss(y_valid, valid_prob)),
                "testBrier": float(brier_score_loss(y_test, test_prob)),
                "validAuc": float(roc_auc_score(y_valid, valid_prob)) if len(set(y_valid)) > 1 else None,
                "testAuc": float(roc_auc_score(y_test, test_prob)) if len(set(y_test)) > 1 else None,
            }
        )
    else:
        valid_pred = model.predict(x_valid)
        test_pred = model.predict(x_test)
        metrics.update(
            {
                "validRmse": float(mean_squared_error(y_valid, valid_pred) ** 0.5),
                "testRmse": float(mean_squared_error(y_test, test_pred) ** 0.5),
            }
        )

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    model_path = out / f"{head}.cbm"
    vectorizer_path = out / f"{head}.vectorizer.joblib"
    metadata_path = out / f"{head}.metadata.json"
    model.save_model(str(model_path))
    joblib.dump(vectorizer, vectorizer_path)
    metadata = {
        "trainerVersion": TRAINER_VERSION,
        "head": head,
        "task": spec.task,
        "label": spec.label,
        "featureLimit": HEAD_FEATURE_LIMITS[head],
        "selectedFeatureNames": feature_names,
        "metrics": metrics,
        "modelPath": model_path.name,
        "vectorizerPath": vectorizer_path.name,
    }
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    return metadata


def train_all_heads(rows: list[dict[str, Any]], output_dir: str | Path) -> dict[str, Any]:
    return {
        "trainerVersion": TRAINER_VERSION,
        "heads": {head: train_head(rows, head, output_dir) for head in HEAD_SPECS},
    }
