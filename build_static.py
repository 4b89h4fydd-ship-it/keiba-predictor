from pathlib import Path
import ast
import base64
import re
import shutil

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "app.py"
DIST = ROOT / "dist"

if DIST.exists():
    shutil.rmtree(DIST)
DIST.mkdir()

source = SRC.read_text(encoding="utf-8")
tree = ast.parse(source)

strings = {}
icons = None
binary_b64 = {}

for node in tree.body:
    if not isinstance(node, ast.Assign) or len(node.targets) != 1:
        continue
    target = node.targets[0]
    if not isinstance(target, ast.Name):
        continue

    name = target.id
    value = node.value

    if isinstance(value, ast.Constant) and isinstance(value.value, str):
        strings[name] = value.value
        continue

    if name == "KRAIZ_ICONS" and isinstance(value, ast.Dict):
        icons = ast.literal_eval(value)
        continue

    if isinstance(value, ast.Call):
        fn = value.func
        if (
            isinstance(fn, ast.Attribute)
            and isinstance(fn.value, ast.Name)
            and fn.value.id == "base64"
            and fn.attr == "b64decode"
            and value.args
            and isinstance(value.args[0], ast.Constant)
            and isinstance(value.args[0].value, str)
        ):
            binary_b64[name] = value.args[0].value

for required in ("INDEX", "CSS", "JS", "MANIFEST", "SW"):
    if required not in strings:
        raise RuntimeError(f"{required} not found in app.py")

js = strings["JS"]

# v133 browsing is Cloudflare/D1 first. Remove two old manual-only
# same-origin Render fallbacks from the static deployment as well.
js = re.sub(
    r"function prefetchNextHistory\(\)\{return;.*?\}\n\nfunction waitForRaceReady",
    "function prefetchNextHistory(){return}\n\nfunction waitForRaceReady",
    js,
    count=1,
    flags=re.S,
)

js = re.sub(
    r"function refreshRaceAfterCollect\(id,attempt\)\{.*?\}\nfunction collectRaceInfo\(no\)\{.*?\}\nfunction stopTimer",
    "function refreshRaceAfterCollect(id,attempt){reloadCurrent()}\n"
    "function collectRaceInfo(no){reloadCurrent()}\n"
    "function stopTimer",
    js,
    count=1,
    flags=re.S,
)

remaining = [
    line.strip()
    for line in js.splitlines()
    if "fetch('/api/v1/" in line or 'fetch("/api/v1/' in line
]
if remaining:
    raise RuntimeError(
        "Render API fetch remains in static build:\n" + "\n".join(remaining[:20])
    )

(DIST / "index.html").write_text(strings["INDEX"], encoding="utf-8")
(DIST / "404.html").write_text(strings["INDEX"], encoding="utf-8")
(DIST / "styles-kraiz-v130.css").write_text(strings["CSS"], encoding="utf-8")
(DIST / "app-v133.js").write_text(js, encoding="utf-8")
(DIST / "manifest-kraiz-v130.webmanifest").write_text(strings["MANIFEST"], encoding="utf-8")
(DIST / "sw.js").write_text(strings["SW"], encoding="utf-8")

(DIST / "_redirects").write_text(
    "/race /index.html 200\n"
    "/venue /index.html 200\n"
    "/* /index.html 200\n",
    encoding="utf-8",
)

(DIST / "_headers").write_text(
    "/\n"
    "  Cache-Control: no-store\n"
    "/index.html\n"
    "  Cache-Control: no-store\n"
    "/sw.js\n"
    "  Cache-Control: no-store\n"
    "  Service-Worker-Allowed: /\n",
    encoding="utf-8",
)

if not icons:
    raise RuntimeError("KRAIZ_ICONS not found")

(DIST / "kraiz-icon-192.png").write_bytes(base64.b64decode(icons["192"]))
(DIST / "kraiz-icon-512.png").write_bytes(base64.b64decode(icons["512"]))

assets = {
    "CINEMATIC_HERO_WEBP": "kraiz-racing-hero.webp",
    "CINEMATIC_DETAIL_WEBP": "kraiz-racing-detail.webp",
    "HERO_HORSE_WEBP": "hero-horse.webp",
    "PACE_PREVIEW_WEBP": "pace-preview.webp",
}

for variable, filename in assets.items():
    if variable not in binary_b64:
        raise RuntimeError(f"{variable} not found in app.py")
    (DIST / filename).write_bytes(base64.b64decode(binary_b64[variable]))

print(f"KRAIZ static build complete: {DIST}")
print(f"Files: {len(list(DIST.iterdir()))}")
