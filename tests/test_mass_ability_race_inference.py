"""Explicit ability-head inference remains isolated from live predictions."""
from unittest.mock import patch
import pytest
from arvexq.prediction.mass_model_runtime import predict_ability_for_race


def test_missing_ability_artifact_is_not_silently_replaced(tmp_path):
    with pytest.raises(FileNotFoundError, match="ability"):
        predict_ability_for_race({"horses": [{"horseNumber": 1}]}, tmp_path)


def test_ability_inference_uses_existing_feature_matrix(tmp_path):
    (tmp_path / "ability.manifest.json").write_text("{}", encoding="utf-8")
    race = {"horses": [{"horseNumber": 1}, {"horseNumber": 2}, {"horseNumber": 3}]}
    matrix = [{"horse": h, "features": {"f": float(h["horseNumber"])}}
              for h in race["horses"]]
    with patch("arvexq.prediction.mass_feature_factory.build_race_feature_matrix",
               return_value=matrix), patch("arvexq.prediction.mass_model_runtime.MassModelRuntime") as runtime:
        runtime.return_value.load_head.return_value.predict.side_effect = [.2, .5, .3]
        scores = predict_ability_for_race(race, tmp_path)
    assert scores == {1: .2, 2: .5, 3: .3}
    assert runtime.return_value.load_head.call_count == 3
