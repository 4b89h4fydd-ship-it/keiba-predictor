#!/usr/bin/env python3
from pathlib import Path

PATH = Path("arvexq/infra/race_stores.py")
text = PATH.read_text(encoding="utf-8")

mass_import = (
    "    'from arvexq.prediction.mass_prerace_bridge import "
    "prepare_mass_prerace_fields, apply_mass_prerace_fields, frozen_mass_fields\\n'\n"
)
select_import = (
    "    'from arvexq.selection.race_selectability_snapshot import "
    "prepare_race_selectability_fields, apply_race_selectability_fields, frozen_selectability_fields\\n'\n"
)
if "mass_prerace_bridge" not in text:
    anchor = "SOURCE = (\n    'class PreparedRaceStore:\\n'"
    replacement = "SOURCE = (\n" + mass_import + "    'class PreparedRaceStore:\\n'"
    if anchor not in text:
        raise SystemExit("race store SOURCE anchor not found")
    text = text.replace(anchor, replacement, 1)
if "race_selectability_snapshot" not in text:
    anchor = mass_import
    if anchor not in text:
        raise SystemExit("mass import anchor not found")
    text = text.replace(anchor, mass_import + select_import, 1)

old = (
    "    '        mass_fields=prepare_mass_prerace_fields(detail)\\n'\n"
    "    '        now = int(time.time())\\n'"
)
new = (
    "    '        mass_fields=prepare_mass_prerace_fields(detail)\\n'\n"
    "    '        selectability_fields=prepare_race_selectability_fields(detail)\\n'\n"
    "    '        now = int(time.time())\\n'"
)
if new not in text:
    if old not in text:
        raise SystemExit("pre-compact snapshot anchor not found")
    text = text.replace(old, new, 1)

old = (
    "    '        if mass_fields:apply_mass_prerace_fields(detail,mass_fields)\\n'\n"
    "    '        payload = json.dumps(detail, ensure_ascii=False, separators=(\",\", \":\"))\\n'"
)
new = (
    "    '        if mass_fields:apply_mass_prerace_fields(detail,mass_fields)\\n'\n"
    "    '        if selectability_fields:apply_race_selectability_fields(detail,selectability_fields)\\n'\n"
    "    '        payload = json.dumps(detail, ensure_ascii=False, separators=(\",\", \":\"))\\n'"
)
if new not in text:
    if old not in text:
        raise SystemExit("post-compact snapshot anchor not found")
    text = text.replace(old, new, 1)

old = (
    "    '                    previous_mass=frozen_mass_fields(previous)\\n'\n"
    "    '                    if previous_mass:apply_mass_prerace_fields(detail,previous_mass)\\n'\n"
    "    '                    audit=_prediction_audit_from_lock(detail)\\n'"
)
new = (
    "    '                    previous_mass=frozen_mass_fields(previous)\\n'\n"
    "    '                    if previous_mass:apply_mass_prerace_fields(detail,previous_mass)\\n'\n"
    "    '                    previous_selectability=frozen_selectability_fields(previous)\\n'\n"
    "    '                    if previous_selectability:apply_race_selectability_fields(detail,previous_selectability)\\n'\n"
    "    '                    audit=_prediction_audit_from_lock(detail)\\n'"
)
if new not in text:
    if old not in text:
        raise SystemExit("previous frozen evidence preservation anchor not found")
    text = text.replace(old, new, 1)

for required in (
    "mass_prerace_bridge",
    "race_selectability_snapshot",
    "mass_fields=prepare_mass_prerace_fields(detail)",
    "selectability_fields=prepare_race_selectability_fields(detail)",
    "if mass_fields:apply_mass_prerace_fields(detail,mass_fields)",
    "if selectability_fields:apply_race_selectability_fields(detail,selectability_fields)",
    "previous_mass=frozen_mass_fields(previous)",
    "previous_selectability=frozen_selectability_fields(previous)",
):
    if required not in text:
        raise SystemExit(f"pre-race evidence store patch missing: {required}")

PATH.write_text(text, encoding="utf-8")
print("mass features and race selectability snapshots wired into PreparedRaceStore")
