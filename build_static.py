from pathlib import Path
import ast
import base64
import shutil

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "app.py"
DIST = ROOT / "dist"
BUILD_VERSION = "v321"

if DIST.exists():
    shutil.rmtree(DIST)
DIST.mkdir()

source = SRC.read_text(encoding="utf-8")
tree = ast.parse(source)
strings = {}
icons = None
binary_b64 = {}

for node in tree.body:
    if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
        name = node.targets[0].id
        value = node.value
        if isinstance(value, ast.Constant) and isinstance(value.value, str):
            strings[name] = value.value
            continue
        if name == "ARVEXQ_ICONS" and isinstance(value, ast.Dict):
            icons = ast.literal_eval(value)
            continue
        if isinstance(value, ast.Call):
            fn = value.func
            if (isinstance(fn, ast.Attribute) and isinstance(fn.value, ast.Name)
                    and fn.value.id == "base64" and fn.attr == "b64decode"
                    and value.args and isinstance(value.args[0], ast.Constant)
                    and isinstance(value.args[0].value, str)):
                binary_b64[name] = value.args[0].value
                continue
    # app.py appends CSS blocks in source order; static must mirror dynamic CSS exactly.
    if (isinstance(node, ast.AugAssign) and isinstance(node.target, ast.Name)
            and isinstance(node.op, ast.Add) and isinstance(node.value, ast.Constant)
            and isinstance(node.value.value, str)):
        name = node.target.id
        strings[name] = strings.get(name, "") + node.value.value

for required in ("INDEX", "CSS", "JS", "MANIFEST", "SW"):
    if required not in strings:
        raise RuntimeError(f"{required} not found in app.py")
if not icons:
    raise RuntimeError("ARVEXQ_ICONS not found")
if "ARVEXQ_TOUCH_ICON_180" not in binary_b64:
    raise RuntimeError("ARVEXQ_TOUCH_ICON_180 not found")

index_html = strings["INDEX"]
css = strings["CSS"]
js = strings["JS"]
manifest = strings["MANIFEST"]
sw = strings["SW"]

# Current shell. Dynamic FastAPI and static Pages intentionally use byte-identical JS/CSS.
(DIST / "index.html").write_text(index_html, encoding="utf-8")
(DIST / "404.html").write_text(index_html, encoding="utf-8")
for route in ("venue", "race"):
    (DIST / route).mkdir()
    (DIST / route / "index.html").write_text(index_html, encoding="utf-8")

(DIST / f"styles-arvexq-{BUILD_VERSION}.css").write_text(css, encoding="utf-8")
(DIST / f"app-{BUILD_VERSION}.js").write_text(js, encoding="utf-8")
(DIST / f"arvexq-app-{BUILD_VERSION}.js").write_text(js, encoding="utf-8")

# Legacy shell compatibility uses redirects, not duplicate 300KB JS/CSS copies.
# This keeps old PWA shells recoverable while the deploy stays small.
compat_css = ("v320","v319","v318","v317","v316","v315","v314","v313","v312","v308","v307","v306","v305","v303","v130")
compat_app = ("v320","v319","v318","v317","v316","v315","v314","v313","v312","v308","v307","v306","v305","v303","v147","v146","v145","v141","v140","v139","v138","v137","v136","v133")
compat_arvexq = ("v320","v319","v318","v317","v316","v315","v314","v313","v312","v308","v307","v306","v305","v303")

# PWA/manifest: current plus compatibility aliases.
for name in ("manifest-arvexq-v175.webmanifest","manifest-arvexq-v173.webmanifest","manifest-arvexq-v130.webmanifest"):
    (DIST / name).write_text(manifest, encoding="utf-8")
(DIST / "sw.js").write_text(sw, encoding="utf-8")
(DIST / "sw-v321-reset.js").write_text(sw, encoding="utf-8")
(DIST / "sw-v320-reset.js").write_text(sw, encoding="utf-8")
(DIST / "sw-v319-reset.js").write_text(sw, encoding="utf-8")
(DIST / "sw-v318-reset.js").write_text(sw, encoding="utf-8")

(DIST / "build-version.txt").write_text(BUILD_VERSION + "\n", encoding="utf-8")
(DIST / "version.json").write_text('{"build":"v321","shell":"race-sync-fix","model":"v317-consensus-rebuild"}\n', encoding="utf-8")
redirects = ["/venue /index.html 200", "/race /index.html 200"]
for v in compat_app:
    redirects.append(f"/app-{v}.js /app-{BUILD_VERSION}.js 302")
for v in compat_arvexq:
    redirects.append(f"/arvexq-app-{v}.js /arvexq-app-{BUILD_VERSION}.js 302")
for v in compat_css:
    redirects.append(f"/styles-arvexq-{v}.css /styles-arvexq-{BUILD_VERSION}.css 302")
(DIST / "_redirects").write_text("\n".join(redirects) + "\n", encoding="utf-8")
# HTML/version/SW must revalidate. Current versioned JS/CSS and stable media can be cached hard.
# Old compatibility aliases deliberately stay no-cache because their filenames are reused.
headers = [
    "/index.html", "  Cache-Control: no-store, no-cache, must-revalidate, max-age=0",
    "/404.html", "  Cache-Control: no-store, no-cache, must-revalidate, max-age=0",
    "/venue/*", "  Cache-Control: no-store, no-cache, must-revalidate, max-age=0",
    "/race/*", "  Cache-Control: no-store, no-cache, must-revalidate, max-age=0",
    "/version.json", "  Cache-Control: no-store, no-cache, must-revalidate, max-age=0",
    "/manifest-arvexq-v175.webmanifest", "  Cache-Control: no-cache, must-revalidate",
    "/sw.js", "  Cache-Control: no-store, no-cache, must-revalidate, max-age=0", "  Service-Worker-Allowed: /",
    "/sw-v321-reset.js", "  Cache-Control: no-store, no-cache, must-revalidate, max-age=0", "  Service-Worker-Allowed: /",
    "/sw-v320-reset.js", "  Cache-Control: no-store, no-cache, must-revalidate, max-age=0", "  Service-Worker-Allowed: /",
    "/sw-v319-reset.js", "  Cache-Control: no-store, no-cache, must-revalidate, max-age=0", "  Service-Worker-Allowed: /",
    "/sw-v318-reset.js", "  Cache-Control: no-store, no-cache, must-revalidate, max-age=0", "  Service-Worker-Allowed: /",
    f"/app-{BUILD_VERSION}.js", "  Cache-Control: public, max-age=31536000, immutable",
    f"/arvexq-app-{BUILD_VERSION}.js", "  Cache-Control: public, max-age=31536000, immutable",
    f"/styles-arvexq-{BUILD_VERSION}.css", "  Cache-Control: public, max-age=31536000, immutable",
    "/arvexq-racing-hero.webp", "  Cache-Control: public, max-age=604800",
    "/arvexq-racing-detail.webp", "  Cache-Control: public, max-age=604800",
    "/hero-horse.webp", "  Cache-Control: public, max-age=604800",
    "/pace-preview.webp", "  Cache-Control: public, max-age=604800",
    "/arvexq-logo.webp", "  Cache-Control: public, max-age=604800",
]
(DIST / "_headers").write_text("\n".join(headers) + "\n", encoding="utf-8")

(DIST / "arvexq-touch-v175.png").write_bytes(base64.b64decode(binary_b64["ARVEXQ_TOUCH_ICON_180"]))
(DIST / "arvexq-icon-v175-192.png").write_bytes(base64.b64decode(icons["192"]))
(DIST / "arvexq-icon-v175-512.png").write_bytes(base64.b64decode(icons["512"]))
(DIST / "arvexq-icon-192.png").write_bytes(base64.b64decode(icons["192"]))
(DIST / "arvexq-icon-512.png").write_bytes(base64.b64decode(icons["512"]))

assets = {
    "CINEMATIC_HERO_WEBP": "arvexq-racing-hero.webp",
    "CINEMATIC_DETAIL_WEBP": "arvexq-racing-detail.webp",
    "HERO_HORSE_WEBP": "hero-horse.webp",
    "PACE_PREVIEW_WEBP": "pace-preview.webp",
    "ARVEXQ_LOGO_WEBP": "arvexq-logo.webp",
}
for var, filename in assets.items():
    if var in binary_b64:
        (DIST / filename).write_bytes(base64.b64decode(binary_b64[var]))

print(f"ARVEXQ static build complete: {DIST}")
print(f"BUILD: {BUILD_VERSION}")
print(f"Files: {len(list(DIST.rglob('*')))}")
