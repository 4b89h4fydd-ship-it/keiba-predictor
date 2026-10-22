"""Load this box's forwarding helper; no UI content, data or network access."""
from pathlib import Path

def read_route_script():
    return Path(__file__).with_name("routes.js").read_text(encoding="utf-8")
