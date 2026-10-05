#!/usr/bin/env python3
from pathlib import Path

PATH = Path("arvexq/infra/race_stores.py")
text = PATH.read_text(encoding="utf-8")

import_line = (
    "    'from arvexq.prediction.mass_prerace_bridge import "
    "prepare_mass_prerace_fields, apply_mass_prerace_fields, frozen_mass_fields\\n'\n"
)
if "mass_prerace_bridge" not in text:
    anchor = "SOURCE = (\n    'class PreparedRaceStore:\\n'"
    replacement = "SOURCE = (\n" + import_line + "    'class PreparedRaceStore:\\n'"
    if anchor not in text:
        raise SystemExit("race store SOURCE anchor not found")
    text = text.replace(anchor, replacement, 1)

old = (
    "    '        now = int(time.time())\\n'\n"
    "    '        detail.setdefault(\"preparedMeta\", {})\\n'"
)
new = (
    "    '        mass_fields=prepare_mass_prerace_fields(detail)\\n'\n"
    "    '        now = int(time.time())\\n'\n"
    "    '        detail.setdefault(\"preparedMeta\", {})\\n'"
)
if new not in text:
    if old not in text:
        raise SystemExit("pre-compact mass snapshot anchor not found")
    text = text.replace(old, new, 1)

old = (
    "    '        clean=_compact_display_snapshot(_strip_excluded(detail))\\n'\n"
    "    '        detail.clear();detail.update(clean)\\n'\n"
    "    '        payload = json.dumps(detail, ensure_ascii=False, separators=(\",\", \":\"))\\n'"
)
new = (
    "    '        clean=_compact_display_snapshot(_strip_excluded(detail))\\n'\n"
    "    '        detail.clear();detail.update(clean)\\n'\n"
    "    '        if mass_fields:apply_mass_prerace_fields(detail,mass_fields)\\n'\n"
    "    '        payload = json.dumps(detail, ensure_ascii=False, separators=(\",\", \":\"))\\n'"
)
if new not in text:
    if old not in text:
        raise SystemExit("post-compact mass snapshot anchor not found")
    text = text.replace(old, new, 1)

old = (
    "    '                    detail[\"preRacePrediction\"]=previous[\"preRacePrediction\"]\\n'\n"
    "    '                    audit=_prediction_audit_from_lock(detail)\\n'"
)
new = (
    "    '                    detail[\"preRacePrediction\"]=previous[\"preRacePrediction\"]\\n'\n"
    "    '                    previous_mass=frozen_mass_fields(previous)\\n'\n"
    "    '                    if previous_mass:apply_mass_prerace_fields(detail,previous_mass)\\n'\n"
    "    '                    audit=_prediction_audit_from_lock(detail)\\n'"
)
if new not in text:
    if old not in text:
        raise SystemExit("previous lock preservation anchor not found")
    text = text.replace(old, new, 1)

for required in (
    "mass_prerace_bridge",
    "mass_fields=prepare_mass_prerace_fields(detail)",
    "if mass_fields:apply_mass_prerace_fields(detail,mass_fields)",
    "previous_mass=frozen_mass_fields(previous)",
):
    if required not in text:
        raise SystemExit(f"mass prerace store patch missing: {required}")

PATH.write_text(text, encoding="utf-8")
print("mass pre-race snapshot bridge wired into PreparedRaceStore")
