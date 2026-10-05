from __future__ import annotations

import importlib.util
import json
import math
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any

RUNTIME_VERSION = "arvexq-mass-model-runtime-v1"


def _sigmoid(raw: float) -> float:
    if raw >= 0:
        z = math.exp(-raw)
        return 1.0 / (1.0 + z)
    z = math.exp(raw)
    return z / (1.0 + z)


def _load_module(path: Path, module_name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load standalone model: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@dataclass
class StandaloneHead:
    head: str
    task: str
    feature_names: list[str]
    module: ModuleType

    def predict_raw(self, features: dict[str, float]) -> float:
        vector = [float(features.get(name, 0.0)) for name in self.feature_names]
        value = self.module.apply_catboost_model(vector)
        if isinstance(value, (list, tuple)):
            value = value[0]
        return float(value)

    def predict(self, features: dict[str, float]) -> float:
        raw = self.predict_raw(features)
        return _sigmoid(raw) if self.task == "binary" else raw


class MassModelRuntime:
    """Lightweight inference over standalone CatBoost Python exports.

    No CatBoost/sklearn dependency is imported here. Loading is explicit, so normal
    ARVEXQ requests pay no model cost unless this runtime is actually enabled.
    """

    def __init__(self, runtime_dir: str | Path):
        self.runtime_dir = Path(runtime_dir)
        self.heads: dict[str, StandaloneHead] = {}

    def load_head(self, head: str) -> StandaloneHead:
        if head in self.heads:
            return self.heads[head]
        manifest_path = self.runtime_dir / f"{head}.manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        model_path = self.runtime_dir / str(manifest["pythonModel"])
        module = _load_module(model_path, f"arvexq_mass_{head}_standalone")
        loaded = StandaloneHead(
            head=head,
            task=str(manifest.get("task") or "regression"),
            feature_names=[str(x) for x in manifest.get("featureNames") or []],
            module=module,
        )
        self.heads[head] = loaded
        return loaded

    def predict_heads(self, features: dict[str, float]) -> dict[str, float]:
        return {
            head: self.load_head(head).predict(features)
            for head in ("ability", "win", "value", "danger")
            if (self.runtime_dir / f"{head}.manifest.json").exists()
        }
