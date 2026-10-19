"""Verify all 200 boxes, actual ownership and unchanged migration semantics."""
from __future__ import annotations
import ast
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from arvexq.components.catalog import all_components, assemble_ui
from arvexq.components.runtime import composed_app_source

from arvexq.components.item_196.audit import audit


if __name__=='__main__':
    report=audit();print(json.dumps(report,ensure_ascii=False,indent=2));raise SystemExit(bool(report['errors']))
