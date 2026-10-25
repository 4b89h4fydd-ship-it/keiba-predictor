"""The existing batch model trainer can target just the ability head."""
import json
import sys
from pathlib import Path
from unittest.mock import patch

from scripts import train_mass_models


def test_ability_only_does_not_train_other_heads(tmp_path):
    dataset = tmp_path / "frozen.jsonl"
    dataset.write_text("".join(
        json.dumps({"raceId": f"r-{i}"}) + "\n" for i in range(40)
    ), encoding="utf-8")
    models = tmp_path / "models"
    runtimes = tmp_path / "runtime"
    with patch.object(sys, "argv", [
        "train_mass_models", str(dataset), str(models), str(runtimes),
        "--head", "ability",
    ]), patch.object(train_mass_models, "train_head", return_value={"head": "ability"}) as train, patch.object(
        train_mass_models, "export_head_runtime", return_value={"head": "ability"}
    ) as export, patch.object(train_mass_models, "train_all_heads") as all_train:
        assert train_mass_models.main() == 0
    train.assert_called_once()
    assert train.call_args.args[1] == "ability"
    export.assert_called_once_with("ability", str(models), str(runtimes))
    all_train.assert_not_called()
