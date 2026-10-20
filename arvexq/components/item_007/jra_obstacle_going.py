"""JRA obstacle-going selection, isolated from turf/dirt HTML parsing."""
from collections.abc import Mapping

def parse_jra_obstacle_going(surface_conditions: Mapping[str, str]) -> str | None:
    # Preserve the established JRA obstacle rule: turf first, then dirt.
    return surface_conditions.get("芝") or surface_conditions.get("ダート") or None
