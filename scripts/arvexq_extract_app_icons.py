#!/usr/bin/env python3
"""One-time lossless extraction of large embedded icon bytes from app.py.

Intentionally does NOT move runtime API endpoints or prediction functions.
Original base64 is decoded to the exact PNG bytes and restored on demand by
arvexq.ui.icon_assets.load_icons. The builder consumes the same loader.
"""
from __future__ import annotations
import ast
import base64
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "app.py"
BUILDER = ROOT / "build_static.py"
STATIC = ROOT / "arvexq" / "ui" / "static"
HELPER = ROOT / "arvexq" / "ui" / "icon_assets.py"
PNG_SIG = b"\x89PNG\r\n\x1a\n"

LOADER = '''"""Runtime and PWA icon asset loader. The original PNG bytes are preserved."""
from __future__ import annotations
import base64
from functools import lru_cache
from pathlib import Path

_STATIC = Path(__file__).resolve().parent / "static"
_FILES = {"192": "arvexq-icon-source-192.png",
          "512": "arvexq-icon-source-512.png"}

@lru_cache(maxsize=1)
def load_icons() -> dict[str, str]:
    """Recreate the historical base64 API without embedding images in app.py."""
    return {size: base64.b64encode((_STATIC / filename).read_bytes()).decode("ascii")
            for size, filename in _FILES.items()}
'''


def run() -> None:
    source = SOURCE.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(SOURCE))
    nodes = [n for n in tree.body
             if isinstance(n, ast.Assign)
             and len(n.targets) == 1
             and isinstance(n.targets[0], ast.Name)
             and n.targets[0].id == "ARVEXQ_ICONS"]
    if len(nodes) != 1:
        raise SystemExit("Expected exactly one ARVEXQ_ICONS assignment")
    node = nodes[0]
    if not isinstance(node.value, ast.Dict):
        raise SystemExit("app.py icons have already been extracted; no-op")
    icons = ast.literal_eval(node.value)
    if not isinstance(icons, dict) or set(icons) != {"192", "512"}:
        raise SystemExit(f"Unexpected icon keys: {sorted(icons)}; refusing to mutate")
    STATIC.mkdir(parents=True, exist_ok=True)
    size_total = 0
    for key in ("192", "512"):
        raw = base64.b64decode(icons[key], validate=True)
        if not raw.startswith(PNG_SIG):
            raise SystemExit(f"Refusing non-PNG icon {key}")
        (STATIC / f"arvexq-icon-source-{key}.png").write_bytes(raw)
        size_total += len(raw)

    old_lines = source.splitlines(keepends=True)
    # Verify precisely the AST node being replaced, rather than deleting an
    # arbitrary coincidentally matching string from an unrelated code path.
    old = "".join(old_lines[node.lineno-1:node.end_lineno])
    if not old.lstrip().startswith("ARVEXQ_ICONS ="):
        raise SystemExit("Unexpected icon assignment, refusing to mutate")
    replacement = ("from arvexq.ui.icon_assets import load_icons as _load_arvexq_icons\n"
                   "ARVEXQ_ICONS = _load_arvexq_icons()\n")
    new_lines = old_lines[:node.lineno-1] + [replacement] + old_lines[node.end_lineno:]
    new_source = "".join(new_lines)
    ast.parse(new_source, filename=str(SOURCE))

    builder = BUILDER.read_text(encoding="utf-8")
    guard = 'if not icons:\n    raise RuntimeError("ARVEXQ_ICONS not found")'
    swap = ('if not icons:\n'
            '    # app.py now stores original PNGs as static assets, not a huge literal.\n'
            '    from arvexq.ui.icon_assets import load_icons\n'
            '    icons = load_icons()\n'
            'if not icons:\n    raise RuntimeError("ARVEXQ_ICONS not found")')
    if guard not in builder:
        raise SystemExit("Missing builder extraction guard, refusing to edit")
    new_builder = builder.replace(guard, swap, 1)
    ast.parse(new_builder, filename=str(BUILDER))

    # Preserve the public variable's keys/content exactly.
    HELPER.write_text(LOADER, encoding="utf-8")
    from importlib.util import module_from_spec, spec_from_file_location
    spec = spec_from_file_location("_arvexq_icon_test", HELPER)
    module = module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    loaded = module.load_icons()
    if loaded != icons:
        raise SystemExit("Original and extracted icon bytes differ")
    SOURCE.write_text(new_source, encoding="utf-8")
    BUILDER.write_text(new_builder, encoding="utf-8")
    after = SOURCE.stat().st_size
    print("APP_ICON_EXTRACTION_OK",
          "before_bytes="+str(len(source.encode("utf-8"))),
          "after_bytes="+str(after),
          "saved_bytes="+str(len(source.encode("utf-8"))-after),
          "raw_icon_bytes="+str(size_total),
          "identical_icons=True")


if __name__ == "__main__":
    run()
