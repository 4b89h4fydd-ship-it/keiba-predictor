from __future__ import annotations

import ast
import base64
import re
from pathlib import Path

APP = Path("app.py")
STATIC = Path("arvexq/ui/static")
TEXT_ASSETS = {
    "INDEX": "index.html",
    "CSS": "styles.css",
    "JS": "app.js",
    "SW": "sw.js",
}


def assigned_name(node: ast.stmt) -> str | None:
    if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
        return node.targets[0].id
    if isinstance(node, ast.AugAssign) and isinstance(node.target, ast.Name) and isinstance(node.op, ast.Add):
        return node.target.id
    return None


def literal_string(node: ast.stmt) -> str | None:
    value = node.value if isinstance(node, (ast.Assign, ast.AugAssign)) else None
    try:
        out = ast.literal_eval(value)
    except Exception:
        return None
    return out if isinstance(out, str) else None


def decoded_base64_assignment(node: ast.stmt) -> tuple[str, bytes, str] | None:
    if not isinstance(node, ast.Assign) or len(node.targets) != 1 or not isinstance(node.targets[0], ast.Name):
        return None
    name = node.targets[0].id
    value = node.value
    if not isinstance(value, ast.Call) or not value.args:
        return None
    func = value.func
    is_b64 = (
        isinstance(func, ast.Attribute)
        and func.attr == "b64decode"
        and isinstance(func.value, ast.Name)
        and func.value.id == "base64"
    )
    if not is_b64:
        return None
    try:
        raw = ast.literal_eval(value.args[0])
    except Exception:
        return None
    if not isinstance(raw, (str, bytes)):
        return None
    try:
        data = base64.b64decode(raw)
    except Exception:
        return None
    if not data:
        return None
    suffix = ".webp" if name.endswith("_WEBP") else (".png" if name.endswith("_PNG") else ".bin")
    filename = name.lower().replace("_", "-") + suffix
    return name, data, filename


def insert_import(text: str) -> str:
    imp = "from arvexq.ui.assets import read_asset, read_binary_asset\n"
    if imp in text:
        return text
    lines = text.splitlines(keepends=True)
    insert_at = 0
    for i, line in enumerate(lines):
        if line.startswith("from __future__ import "):
            insert_at = i + 1
            continue
        if i >= insert_at and (line.startswith("from arvexq.") or line.startswith("import ") or line.startswith("from ")):
            insert_at = i + 1
            continue
        if line.strip() and i > insert_at:
            break
    lines.insert(insert_at, imp)
    return "".join(lines)


def main() -> None:
    source = APP.read_text(encoding="utf-8")
    tree = ast.parse(source)
    STATIC.mkdir(parents=True, exist_ok=True)

    text_nodes: dict[str, list[ast.stmt]] = {k: [] for k in TEXT_ASSETS}
    text_values: dict[str, str] = {k: "" for k in TEXT_ASSETS}
    text_valid: dict[str, bool] = {k: True for k in TEXT_ASSETS}
    seen_assign: dict[str, bool] = {k: False for k in TEXT_ASSETS}
    binary_items: list[tuple[ast.Assign, str, bytes, str]] = []

    for node in tree.body:
        name = assigned_name(node)
        if name in TEXT_ASSETS:
            value = literal_string(node)
            if value is None:
                text_valid[name] = False
                continue
            text_nodes[name].append(node)
            if isinstance(node, ast.Assign):
                text_values[name] = value
                seen_assign[name] = True
            elif isinstance(node, ast.AugAssign) and seen_assign[name]:
                text_values[name] += value
            else:
                text_valid[name] = False

        decoded = decoded_base64_assignment(node)
        if decoded is not None:
            bname, data, filename = decoded
            if len(data) >= 8_000:
                binary_items.append((node, bname, data, filename))

    replacements: list[tuple[int, int, str]] = []
    extracted = []

    for name, filename in TEXT_ASSETS.items():
        nodes = text_nodes[name]
        if not nodes or not text_valid[name] or not seen_assign[name]:
            continue
        value = text_values[name]
        if len(value) < 500:
            continue
        (STATIC / filename).write_text(value, encoding="utf-8")
        first = nodes[0]
        replacements.append((first.lineno, first.end_lineno or first.lineno, f'{name} = read_asset("{filename}")\n'))
        for node in nodes[1:]:
            replacements.append((node.lineno, node.end_lineno or node.lineno, ""))
        extracted.append(f"{name}:{len(value)}")

    for node, name, data, filename in binary_items:
        (STATIC / filename).write_bytes(data)
        replacements.append((node.lineno, node.end_lineno or node.lineno, f'{name} = read_binary_asset("{filename}")\n'))
        extracted.append(f"{name}:{len(data)}")

    if not replacements:
        print("No embedded UI assets need extraction")
        return

    lines = source.splitlines(keepends=True)
    for start, end, replacement in sorted(replacements, key=lambda x: x[0], reverse=True):
        lines[start - 1:end] = [replacement] if replacement else []
    new_source = insert_import("".join(lines))
    APP.write_text(new_source, encoding="utf-8")
    print("Extracted:", ", ".join(extracted))


if __name__ == "__main__":
    main()
