"""Point-in-time, research-only feature interactions on *already frozen* inputs.

No raw horse histories, target race results, settlements or external predictions are
read. Do not use these rank signals as calibrated probabilities/fair odds.
"""
from __future__ import annotations

from math import isfinite
from typing import Any

VERSION = 'arvexq-ranking-feature-signals-v1'
MODES = ('baseline', 'enhanced', 'no-position', 'no-market-gap')

# Exact keys permitted by mass_feature_selection.snapshot_feature_allowed.
# Higher percentile means stronger historical ability within the *pre-off* field.
HISTORY_RELATIVE = {
    'form': 'relative::history::all::w5::finish_quality::mean::percentile',
    'position': 'relative::history::all::w5::position_quality::mean::percentile',
    'opponent': 'relative::history::all::w5::opponent_level::mean::percentile',
    'speed': 'relative::history::all::w5::speed::mean::percentile',
    'late_speed': 'relative::history::all::w5::late_speed::mean::percentile',
}


def _finite(features: dict[str, Any], key: str) -> float | None:
    value = features.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    return number if isfinite(number) else None


def _position_feature(name: str) -> bool:
    return any(token in name for token in ('position_quality', 'corner_position', 'corner1_position', 'corner3_position', 'corner_gain'))


def enrich_frozen_features(features: dict[str, float], *, head: str, mode: str,
                           field_size: int) -> dict[str, float]:
    """Construct interactions from verified frozen features only.

    'baseline' reproduces the existing model inputs. 'enhanced' adds
    non-market historical interactions, plus market disagreement for ANA.
    'no-position' removes historical positional evidence, and
    'no-market-gap' removes only the derived market-disagreement features.
    All modes keep the same race roster and outcome labels.
    """
    if mode not in MODES or head not in ('ability', 'ana'):
        raise ValueError('unknown feature experiment')
    out = dict(features)
    if mode == 'baseline':
        return out
    if mode == 'no-position':
        out = {k: v for k, v in out.items() if not _position_feature(k)}
    h = {label: _finite(out, key) for label, key in HISTORY_RELATIVE.items()}
    if mode != 'no-position':
        if h['position'] is not None and h['form'] is not None:
            out['research::position_x_form'] = h['position'] * h['form']
        if h['position'] is not None and h['speed'] is not None:
            out['research::position_x_speed'] = h['position'] * h['speed']
    if h['opponent'] is not None and h['form'] is not None:
        out['research::opponent_x_form'] = h['opponent'] * h['form']
    if h['speed'] is not None and h['late_speed'] is not None:
        out['research::speed_x_late_speed'] = h['speed'] * h['late_speed']
    # For Ability, market independence is mandatory; no market-derived values.
    if head != 'ana' or mode == 'no-market-gap' or field_size < 2:
        return out
    popularity = _finite(out, 'market::popularity')
    if popularity is None or popularity < 1 or popularity > field_size:
        return out
    market_strength = 1.0 - (popularity - 1.0) / (field_size - 1.0)
    for label, historical_percentile in h.items():
        if historical_percentile is None or not 0 <= historical_percentile <= 1:
            continue
        # Positive: the independent historical ranking exceeds market ranking.
        out[f'research::{label}_minus_market'] = historical_percentile - market_strength
    return out


def history_coverage(races: list[dict[str, Any]]) -> dict[str, Any]:
    """Report real availability without treating missing data as zero."""
    entries = [entry for race in races for entry in race['rows']]
    total = len(entries)
    counts = {label: sum(_finite(entry['features'], key) is not None
                         for entry in entries)
              for label, key in HISTORY_RELATIVE.items()}
    return {'races': len(races), 'horses': total,
            'availability': {name: {'observed': count,
                                    'fraction': round(count / total, 4) if total else None}
                             for name, count in counts.items()}}
