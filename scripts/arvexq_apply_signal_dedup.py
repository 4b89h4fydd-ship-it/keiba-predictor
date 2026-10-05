#!/usr/bin/env python3
# Idempotent v4 patcher; touching this file also validates the generated main head.
from pathlib import Path

PATH = Path('arvexq/prediction/factor_model.py')
text = PATH.read_text(encoding='utf-8')

text = text.replace(
    'MODEL_VERSION = "arvexq-four-pillar-consensus-v3"',
    'MODEL_VERSION = "arvexq-four-pillar-consensus-v4"',
)

families = '''PRIMARY_PILLARS = ("ability", "record", "suitability", "pace")

# Correlated measurements from the same underlying observation are collapsed first.
# This prevents one past run from becoming several independent votes merely because
# it produced peak/median, career/recent and win/top3 statistics at the same time.
SIGNAL_FAMILIES = {
    "ability": (
        ("ability_speed_peak", "ability_speed_median"),
        ("ability_peak_finish",),
        ("ability_sectional",),
        ("ability_true_run",),
        ("ability_pure",),
        ("ability_research",),
    ),
    "record": (
        ("record_career", "record_recent"),
        ("record_win_rate", "record_top3_rate"),
        ("record_level", "record_class_edge", "record_class_research"),
        ("record_representative",),
        ("record_race_performance",),
        ("record_form_research",),
    ),
    "suitability": (
        ("suit_distance_history", "suit_track_history", "suit_going_history", "suit_surface_history"),
        ("suit_distance_model", "suit_track_model", "suit_going_model", "suit_surface_model"),
        ("suit_research",),
    ),
    "pace": (
        ("pace_scenario",),
        ("pace_state",),
        ("pace_research",),
        ("pace_track_speed_fit",),
        ("pace_hidden_effort",),
    ),
    "support": (
        ("support_pedigree", "support_pedigree_distance", "support_pedigree_surface", "support_pedigree_research"),
        ("support_body", "support_body_change", "support_carried_weight"),
        ("support_weather",),
        ("support_draw",),
        ("support_condition_change", "support_freshness"),
        ("support_age_sex",),
        ("support_jockey", "support_trainer", "support_connections"),
        ("support_bias", "support_bias_model"),
    ),
}
'''
if 'SIGNAL_FAMILIES = {' not in text:
    text = text.replace(
        'PRIMARY_PILLARS = ("ability", "record", "suitability", "pace")\n',
        families,
        1,
    )

old = '''        scores: dict[str, float | None] = {}
        counts: dict[str, int] = {}
        for pillar, metrics in groups.items():
            vals = [relative_by_metric[m][i] for m in metrics]
            scores[pillar] = _pillar(vals)
            counts[pillar] = sum(v is not None for v in vals)
        row["pillarScores"] = scores
        row["evidenceCounts"] = counts
'''
new = '''        scores: dict[str, float | None] = {}
        counts: dict[str, int] = {}
        family_counts: dict[str, int] = {}
        for pillar, metrics in groups.items():
            vals = [relative_by_metric[m][i] for m in metrics]
            counts[pillar] = sum(v is not None for v in vals)

            # Collapse correlated metrics inside each evidence family before the
            # pillar median. Each family therefore contributes at most one signal.
            collapsed: list[float] = []
            for family in SIGNAL_FAMILIES[pillar]:
                family_value = _pillar([relative_by_metric[m][i] for m in family])
                if family_value is not None:
                    collapsed.append(family_value)
            scores[pillar] = _pillar(collapsed)
            family_counts[pillar] = len(collapsed)
        row["pillarScores"] = scores
        row["evidenceCounts"] = counts
        row["evidenceFamilyCounts"] = family_counts
'''
if old in text:
    text = text.replace(old, new, 1)
elif new not in text:
    raise SystemExit('factor aggregation block not found; refusing unsafe patch')

PATH.write_text(text, encoding='utf-8')
print('signal-family dedup wired', 'v4' if 'consensus-v4' in text else 'version-missing')
