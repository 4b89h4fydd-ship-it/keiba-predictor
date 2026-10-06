from __future__ import annotations

from pathlib import Path

TARGET = Path("build_static.py")


def main() -> None:
    text = TARGET.read_text(encoding="utf-8")
    original = text

    if 'STATIC = ROOT / "arvexq" / "ui" / "static"' not in text:
        text = text.replace(
            'DIST = ROOT / "dist"\n',
            'DIST = ROOT / "dist"\nSTATIC = ROOT / "arvexq" / "ui" / "static"\n',
            1,
        )

    needle = '''        if isinstance(value, ast.Call):\n            fn = value.func\n            if (\n                isinstance(fn, ast.Attribute)\n'''
    replacement = '''        if isinstance(value, ast.Call):\n            fn = value.func\n            if (\n                isinstance(fn, ast.Name)\n                and fn.id in {"read_asset", "read_binary_asset"}\n                and value.args\n                and isinstance(value.args[0], ast.Constant)\n                and isinstance(value.args[0].value, str)\n            ):\n                asset_path = STATIC / value.args[0].value\n                if not asset_path.is_file():\n                    raise RuntimeError(f"extracted asset not found: {asset_path}")\n                if fn.id == "read_asset":\n                    strings[name] = asset_path.read_text(encoding="utf-8")\n                else:\n                    binary_b64[name] = base64.b64encode(asset_path.read_bytes()).decode("ascii")\n                continue\n            if (\n                isinstance(fn, ast.Attribute)\n'''

    if 'fn.id in {"read_asset", "read_binary_asset"}' not in text:
        if needle not in text:
            raise SystemExit("PATCH_ABORT: build_static call parser anchor not found")
        text = text.replace(needle, replacement, 1)

    # v325 must keep redirects for the immediately previous installed shell (v324).
    # This prevents a stale iPhone PWA index from requesting an asset that no longer exists.
    text = text.replace('compat_css = ("v323",', 'compat_css = ("v324","v323",')
    text = text.replace('compat_app = ("v323",', 'compat_app = ("v324","v323",')
    text = text.replace('compat_arvexq = ("v323",', 'compat_arvexq = ("v324","v323",')

    if text == original:
        print("No build_static changes needed")
        return

    TARGET.write_text(text, encoding="utf-8")
    print("build_static.py patched for extracted UI assets and v324 compatibility")


if __name__ == "__main__":
    main()
