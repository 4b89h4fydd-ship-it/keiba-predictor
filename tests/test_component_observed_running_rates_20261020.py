from importlib import import_module


def test_read_only_running_style_fields():
    for i,key in zip(range(98,103),("escape","front","stalk","close","fade")):
        read=import_module(f"arvexq.components.item_{i:03d}.observed_rate").read
        assert read({}) is None
        assert read({"styleRates":{key:0.45}})==0.45
        assert read({"runningStyleRates":{key:40}})==40
        assert read({"styleRates":{key:float("nan")}}) is None
