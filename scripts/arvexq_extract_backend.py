from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

APP = Path("app.py")


@dataclass(frozen=True)
class Cluster:
    start: str
    end: str
    module: Path
    installer: str


CLUSTERS = (
    Cluster(
        start="NarArchiveParser",
        end="CentralStore",
        module=Path("arvexq/infra/legacy_stores.py"),
        installer="install_legacy_stores",
    ),
    Cluster(
        start="PreparedRaceStore",
        end="RaceDataBank",
        module=Path("arvexq/infra/race_stores.py"),
        installer="install_race_stores",
    ),
    Cluster(
        start="_integrated_evaluation",
        end="_race_volatility",
        module=Path("arvexq/domain/legacy_evaluation.py"),
        installer="install_evaluation_core",
    ),
)


def _node_name(node: ast.AST) -> str | None:
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        return node.name
    return None


def _start_line(node: ast.AST) -> int:
    lineno = getattr(node, "lineno", 0)
    decorators = getattr(node, "decorator_list", ())
    if decorators:
        lineno = min([lineno, *[getattr(d, "lineno", lineno) for d in decorators]])
    return lineno


def _contains_route_decorator(nodes: list[ast.AST]) -> bool:
    for node in nodes:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for deco in node.decorator_list:
            text = ast.unparse(deco) if hasattr(ast, "unparse") else ""
            if text.startswith("app.") or "router." in text:
                return True
    return False


def _module_text(fragment: str, installer: str, label: str) -> str:
    # Keep the legacy source byte-for-byte inside a role-specific migration module.
    # exec(..., namespace, namespace) means method/function globals still resolve
    # against app.py exactly as before, so extraction does not alter behaviour.
    literal_lines = "\n".join(f"    {line!r}" for line in fragment.splitlines(keepends=True))
    return (
        "from __future__ import annotations\n\n"
        f"# Transitional extraction of {label} from app.py.\n"
        "# The block is executed in the caller namespace to preserve legacy global lookup.\n"
        "SOURCE = (\n"
        f"{literal_lines}\n"
        ")\n\n"
        f"def {installer}(namespace: dict) -> None:\n"
        f"    code = compile(SOURCE, '<arvexq:{label}>', 'exec')\n"
        "    exec(code, namespace, namespace)\n"
    )


def main() -> None:
    source = APP.read_text(encoding="utf-8")
    tree = ast.parse(source)
    lines = source.splitlines(keepends=True)
    top = list(tree.body)
    names = {_node_name(node): i for i, node in enumerate(top) if _node_name(node)}

    replacements: list[tuple[int, int, str]] = []
    extracted: list[str] = []

    for cluster in CLUSTERS:
        marker = f"# ARVEXQ_EXTRACTED:{cluster.installer}"
        if marker in source:
            continue
        if cluster.start not in names or cluster.end not in names:
            print(f"Skip {cluster.installer}: boundary already absent")
            continue
        a = names[cluster.start]
        b = names[cluster.end]
        if b < a:
            raise SystemExit(f"PATCH_ABORT: invalid cluster order {cluster.start}..{cluster.end}")
        nodes = top[a : b + 1]
        if _contains_route_decorator(nodes):
            raise SystemExit(f"PATCH_ABORT: route decorator found in {cluster.installer}")

        start_line = _start_line(nodes[0])
        end_line = getattr(nodes[-1], "end_lineno", None) or getattr(nodes[-1], "lineno", start_line)
        fragment = "".join(lines[start_line - 1 : end_line])
        if len(fragment) < 1500:
            raise SystemExit(f"PATCH_ABORT: suspiciously small cluster {cluster.installer}: {len(fragment)} bytes")

        cluster.module.parent.mkdir(parents=True, exist_ok=True)
        cluster.module.write_text(
            _module_text(fragment, cluster.installer, cluster.installer.removeprefix("install_")),
            encoding="utf-8",
        )
        import_path = ".".join(cluster.module.with_suffix("").parts)
        replacement = (
            f"{marker}\n"
            f"from {import_path} import {cluster.installer} as _arvexq_installer\n"
            "_arvexq_installer(globals())\n"
            "del _arvexq_installer\n"
        )
        replacements.append((start_line, end_line, replacement))
        extracted.append(f"{cluster.installer}:{len(fragment.encode('utf-8')):,}B:{start_line}-{end_line}")

    if not replacements:
        print("No backend blocks need extraction")
        return

    for start, end, replacement in sorted(replacements, reverse=True):
        lines[start - 1 : end] = [replacement]
    APP.write_text("".join(lines), encoding="utf-8")

    # Strong guards: generated app remains valid and every installer marker is present.
    new_source = APP.read_text(encoding="utf-8")
    ast.parse(new_source)
    for cluster in CLUSTERS:
        marker = f"# ARVEXQ_EXTRACTED:{cluster.installer}"
        if marker not in new_source:
            raise SystemExit(f"PATCH_ABORT: missing installer marker {cluster.installer}")
        if not cluster.module.is_file():
            raise SystemExit(f"PATCH_ABORT: missing generated module {cluster.module}")
        ast.parse(cluster.module.read_text(encoding="utf-8"))

    print("Extracted backend blocks:")
    for item in extracted:
        print(" -", item)
    print(f"app.py now {APP.stat().st_size:,} bytes")


if __name__ == "__main__":
    main()
