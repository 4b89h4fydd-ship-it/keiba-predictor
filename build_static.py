from pathlib import Path
import ast
import base64
import hashlib
import json
import re
import shutil

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "app.py"
DIST = ROOT / "dist"
# UI assets are intentionally stored outside app.py after modularization.
STATIC = ROOT / "arvexq" / "ui" / "static"

if DIST.exists():
    shutil.rmtree(DIST)
DIST.mkdir()

source = SRC.read_text(encoding="utf-8")
tree = ast.parse(source)


def _build_version_from_app(tree: ast.AST) -> str:
    for node in getattr(tree, "body", []):
        if not (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id == "app"
            and isinstance(node.value, ast.Call)
        ):
            continue
        fn = node.value.func
        if not (isinstance(fn, ast.Name) and fn.id == "FastAPI"):
            continue
        for kw in node.value.keywords:
            if kw.arg == "version" and isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, str):
                m = re.search(r"\bv\d+\b", kw.value.value)
                if m:
                    return m.group(0)
    raise RuntimeError("ARVEXQ build version not found in FastAPI(version=...) literal")


BUILD_VERSION = _build_version_from_app(tree)
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
            if (
                isinstance(fn, ast.Name)
                and fn.id in {"read_asset", "read_binary_asset"}
                and value.args
                and isinstance(value.args[0], ast.Constant)
                and isinstance(value.args[0].value, str)
            ):
                asset_path = STATIC / value.args[0].value
                if not asset_path.is_file():
                    raise RuntimeError(f"extracted asset not found: {asset_path}")
                if fn.id == "read_asset":
                    strings[name] = asset_path.read_text(encoding="utf-8")
                else:
                    binary_b64[name] = base64.b64encode(asset_path.read_bytes()).decode("ascii")
                continue
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
                continue
    if (
        isinstance(node, ast.AugAssign)
        and isinstance(node.target, ast.Name)
        and isinstance(node.op, ast.Add)
        and isinstance(node.value, ast.Constant)
        and isinstance(node.value.value, str)
    ):
        name = node.target.id
        strings[name] = strings.get(name, "") + node.value.value

for required in ("INDEX", "CSS", "JS", "MANIFEST", "SW"):
    if required not in strings:
        raise RuntimeError(f"{required} not found in app.py or extracted UI assets")
if not icons:
    # app.py now stores original PNGs as static assets, not a huge literal.
    from arvexq.ui.icon_assets import load_icons
    icons = load_icons()
if not icons:
    raise RuntimeError("ARVEXQ_ICONS not found")
if "ARVEXQ_TOUCH_ICON_180" not in binary_b64:
    raise RuntimeError("ARVEXQ_TOUCH_ICON_180 not found")

BET_PATH = STATIC / "betting"
BET_ASSETS = ("legacy_v213_order_model.js", "podium_axis_guard.js", "bet_readiness.js", "no_axis_strategy.js", "main_strategy.js", "trifecta_strategy.js", "insurance_strategy.js", "three_way_engine.js", "bet_view.js", "bet_ui.css")
for filename in BET_ASSETS:
    if not (BET_PATH / filename).is_file():
        raise RuntimeError(f"missing independent betting asset: {filename}")
bet_hash = hashlib.sha256(b"|".join((BET_PATH / filename).read_bytes() for filename in BET_ASSETS)).hexdigest()[:12]

MORNING_PATH = STATIC / "morning"
MORNING_MODULES = ("ticket_lane_classifier.js", "selection_cut.js", "frozen_ticket_evidence.js")
for filename in MORNING_MODULES:
    if not (MORNING_PATH / filename).is_file():
        raise RuntimeError(f"missing morning module: {filename}")
morning_hash = hashlib.sha256(b"|".join((MORNING_PATH / filename).read_bytes()
                                     for filename in MORNING_MODULES)).hexdigest()[:12]

STYLE_DIR = STATIC / "styles"
STYLE_MODULES = ("legacy_v118_v221.css", "race_v222_plus.css")
for filename in STYLE_MODULES:
    if not (STYLE_DIR / filename).is_file():
        raise RuntimeError(f"missing independently loaded CSS: {filename}")
style_hash = hashlib.sha256(b"|".join((STYLE_DIR / filename).read_bytes() for filename in STYLE_MODULES)).hexdigest()[:12]

RESEARCH_PATH = STATIC / "research"
RESEARCH_ASSETS = ("local_evidence.js", "research_view.js", "research_view.css", "static_racecard.js", "live_odds.js", "saved_snapshot.js", "diagnosis_view.js", "race_identity.js")
for filename in RESEARCH_ASSETS:
    if not (RESEARCH_PATH / filename).is_file():
        raise RuntimeError(f"missing research asset: {filename}")
research_hash = hashlib.sha256(b"|".join((RESEARCH_PATH / filename).read_bytes() for filename in RESEARCH_ASSETS)).hexdigest()[:12]

index_html = strings["INDEX"]
index_html = index_html.replace("__ARVEXQ_RESEARCH_HASH__", research_hash)
index_html = index_html.replace("__ARVEXQ_STYLE_MODULE_HASH__", style_hash)
index_html = index_html.replace("__ARVEXQ_MORNING_MODULE_HASH__", morning_hash)
index_html = index_html.replace("__ARVEXQ_BET_ASSET_FINGERPRINT__", bet_hash)
css = strings["CSS"]
js = strings["JS"]
# Refresh unchanged v329 filenames when actual UI files change. Avoid stale
# iPhone/PWA JS/CSS while preserving the approved top-screen composition.
core_asset_hash = hashlib.sha256((js + "\0" + css).encode("utf-8")).hexdigest()[:12]
index_html, fingerprint_replacements = re.subn(
    r'(/app-' + re.escape(BUILD_VERSION) + r'\.js\?fix=)[A-Za-z0-9._-]+',
    lambda match: match.group(1) + core_asset_hash,
    index_html,
)
if fingerprint_replacements != 1 or ("?fix=" + core_asset_hash) not in index_html:
    raise RuntimeError("App JS content fingerprint was not injected; refusing stale iPhone deploy")
manifest = strings["MANIFEST"]
sw = strings["SW"]

# Prediction/mark logic is owned by arvexq/ui/static/app.js and the server-side
# four-pillar engine. build_static.py must never redefine prediction functions.

SCRATCH_OVERLAY_CSS = r'''
<style id="arvexq-scratch-overlay-css">
.arvexq-scratched{position:relative!important;opacity:.62!important;filter:grayscale(.72)!important;background:linear-gradient(90deg,rgba(127,29,29,.22),rgba(30,41,59,.16))!important;border-color:rgba(248,113,113,.58)!important}
.arvexq-scratched .arvexq-scratch-badge{display:inline-flex!important;align-items:center;justify-content:center;min-height:22px;padding:2px 8px;margin:0 6px;border:1px solid rgba(254,202,202,.75);border-radius:999px;background:#b91c1c;color:#fff;font-size:12px;font-weight:900;letter-spacing:.04em;line-height:1.2;white-space:nowrap;box-shadow:0 1px 8px rgba(127,29,29,.35)}
.arvexq-scratched input[type="checkbox"],.arvexq-scratched [role="checkbox"]{pointer-events:none!important;opacity:.28!important;filter:grayscale(1)!important}
.arvexq-scratched [class*="name"],.arvexq-scratched [data-horse-name]{text-decoration:line-through;text-decoration-thickness:2px;text-decoration-color:rgba(248,113,113,.9)}
</style>
'''
SCRATCH_OVERLAY_JS = r'''
<script id="arvexq-scratch-overlay-js">
(()=>{
  const TERM=/^(?:出走取消|取消|競走除外|除外|SCRATCHED)$/i;
  const CLASS_HINT=/(horse|runner|entry|uma|row|card)/i;
  const statusText=(el)=>String(el?.getAttribute?.('data-status')||el?.getAttribute?.('aria-label')||'').trim();
  const isScratchText=(s)=>TERM.test(String(s||'').replace(/\s+/g,''));
  const rowFor=(el)=>{
    if(!el)return null;
    const hit=el.closest?.('[data-horse-number],[data-runner],[data-entry],tr,.horse-row,.runner-row,.entry-row,.horse-card,.runner-card,.entry-card');
    if(hit)return hit;
    let cur=el;
    for(let i=0;i<5&&cur&&cur!==document.body;i++,cur=cur.parentElement){
      const txt=(cur.textContent||'').trim();
      if(txt.length<=700&&(CLASS_HINT.test(cur.className||'')||cur.querySelector?.('input[type="checkbox"],[role="checkbox"]')))return cur;
    }
    return el.parentElement;
  };
  const mark=(row)=>{
    if(!row||row.classList?.contains('arvexq-scratched'))return;
    row.classList?.add('arvexq-scratched');row.setAttribute?.('data-arvexq-scratched','true');
    row.setAttribute?.('aria-label',`${row.getAttribute?.('aria-label')||''} 出走取消`.trim());
    row.querySelectorAll?.('input[type="checkbox"],[role="checkbox"]').forEach(x=>{if('disabled' in x)x.disabled=true;x.setAttribute?.('aria-disabled','true');if(x.getAttribute?.('role')==='checkbox')x.setAttribute?.('aria-checked','false')});
    if(!row.querySelector?.('.arvexq-scratch-badge')){const badge=document.createElement('span');badge.className='arvexq-scratch-badge';badge.textContent='出走取消';const anchor=row.querySelector?.('[data-horse-name],[class*="horse-name"],[class*="runner-name"],[class*="entry-name"],[class*="name"]');if(anchor?.parentNode)anchor.insertAdjacentElement('afterend',badge);else row.prepend?.(badge)}
  };
  let queued=false;const scan=()=>{queued=false;document.querySelectorAll('[data-scratched="true"],[data-status*="取消"],[data-status*="除外"],[aria-label*="出走取消"],[aria-label*="競走除外"]').forEach(el=>mark(rowFor(el)));document.querySelectorAll('span,small,strong,b,em,div,td').forEach(el=>{const own=Array.from(el.childNodes||[]).filter(n=>n.nodeType===3).map(n=>n.nodeValue).join('').trim();if(isScratchText(own)||isScratchText(statusText(el)))mark(rowFor(el))})};
  const schedule=()=>{if(queued)return;queued=true;requestAnimationFrame(scan)};
  document.addEventListener('click',e=>{const row=e.target?.closest?.('.arvexq-scratched');if(!row)return;if(e.target?.matches?.('input[type="checkbox"],[role="checkbox"],[data-select-horse],.horse-check,.runner-check,.entry-check')){e.preventDefault();e.stopPropagation()}},true);
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',schedule,{once:true});else schedule();
  new MutationObserver(schedule).observe(document.documentElement,{subtree:true,childList:true,attributes:true,attributeFilter:['data-scratched','data-status','aria-label']});
})();
</script>
'''
if "</head>" in index_html:
    index_html = index_html.replace("</head>", SCRATCH_OVERLAY_CSS + "\n</head>", 1)
if "</body>" in index_html:
    index_html = index_html.replace("</body>", SCRATCH_OVERLAY_JS + "\n</body>", 1)

(DIST / "index.html").write_text(index_html, encoding="utf-8")
(DIST / "404.html").write_text(index_html, encoding="utf-8")
for route in ("venue", "race"):
    (DIST / route).mkdir()
    (DIST / route / "index.html").write_text(index_html, encoding="utf-8")

(DIST / f"styles-arvexq-{BUILD_VERSION}.css").write_text(css, encoding="utf-8")
(DIST / f"app-{BUILD_VERSION}.js").write_text(js, encoding="utf-8")
(DIST / f"arvexq-app-{BUILD_VERSION}.js").write_text(js, encoding="utf-8")

compat_css = ("v328","v327","v326","v325","v324","v323","v322","v321","v320","v319","v318","v317","v316","v315","v314","v313","v312","v308","v307","v306","v305","v303","v130")
compat_app = ("v328","v327","v326","v325","v324","v323","v322","v321","v320","v319","v318","v317","v316","v315","v314","v313","v312","v308","v307","v306","v305","v303","v147","v146","v145","v141","v140","v139","v138","v137","v136","v133")
compat_arvexq = ("v328","v327","v326","v325","v324","v323","v322","v321","v320","v319","v318","v317","v316","v315","v314","v313","v312","v308","v307","v306","v305","v303")
for name in ("manifest-arvexq-v175.webmanifest","manifest-arvexq-v173.webmanifest","manifest-arvexq-v130.webmanifest"):
    (DIST / name).write_text(manifest, encoding="utf-8")
(DIST / "sw.js").write_text(sw, encoding="utf-8")
(DIST / f"sw-{BUILD_VERSION}-reset.js").write_text(sw, encoding="utf-8")
for legacy_sw in ("v328", "v327", "v326", "v325", "v324", "v323", "v322", "v321", "v320", "v319", "v318"):
    (DIST / f"sw-{legacy_sw}-reset.js").write_text(sw, encoding="utf-8")

# Keep betting modules as separate browser resources, not inlined into app.js.
(DIST / "betting").mkdir(exist_ok=True)
for filename in BET_ASSETS:
    shutil.copy2(BET_PATH / filename, DIST / "betting" / filename)

(DIST / "morning").mkdir(exist_ok=True)
for filename in MORNING_MODULES:
    shutil.copy2(MORNING_PATH / filename, DIST / "morning" / filename)

# Preserve CSS cascade while serving large style groups separately.
(DIST / "styles").mkdir(exist_ok=True)
for filename in STYLE_MODULES:
    shutil.copy2(STYLE_DIR / filename, DIST / "styles" / filename)

(DIST / "research").mkdir(exist_ok=True)
for filename in RESEARCH_ASSETS:
    shutil.copy2(RESEARCH_PATH / filename, DIST / "research" / filename)

# Independent UI feature modules kept outside the main app bundle.
for extra_asset in ("previous_ai_results.js",):
    src = STATIC / extra_asset
    if not src.is_file():
        raise RuntimeError(f"extra UI asset not found: {src}")
    shutil.copy2(src, DIST / extra_asset)

(DIST / "build-version.txt").write_text(BUILD_VERSION + "\n", encoding="utf-8")
model_version = strings.get("AI_EVALUATION_VERSION", "").removeprefix("evidence-")
(DIST / "version.json").write_text(json.dumps({"build":BUILD_VERSION,"shell":"four-pillar-authoritative","model":model_version},ensure_ascii=False,separators=(",",":"))+"\n",encoding="utf-8")
redirects=["/venue /index.html 200","/race /index.html 200"]
for v in compat_app:redirects.append(f"/app-{v}.js /app-{BUILD_VERSION}.js 302")
for v in compat_arvexq:redirects.append(f"/arvexq-app-{v}.js /arvexq-app-{BUILD_VERSION}.js 302")
for v in compat_css:redirects.append(f"/styles-arvexq-{v}.css /styles-arvexq-{BUILD_VERSION}.css 302")
(DIST / "_redirects").write_text("\n".join(redirects)+"\n",encoding="utf-8")

headers=[
    "/index.html","  Cache-Control: no-store, no-cache, must-revalidate, max-age=0",
    "/404.html","  Cache-Control: no-store, no-cache, must-revalidate, max-age=0",
    "/venue/*","  Cache-Control: no-store, no-cache, must-revalidate, max-age=0",
    "/race/*","  Cache-Control: no-store, no-cache, must-revalidate, max-age=0",
    "/version.json","  Cache-Control: no-store, no-cache, must-revalidate, max-age=0",
    "/manifest-arvexq-v175.webmanifest","  Cache-Control: no-cache, must-revalidate",
    "/sw.js","  Cache-Control: no-store, no-cache, must-revalidate, max-age=0","  Service-Worker-Allowed: /",
    f"/sw-{BUILD_VERSION}-reset.js","  Cache-Control: no-store, no-cache, must-revalidate, max-age=0","  Service-Worker-Allowed: /",
    "/sw-v328-reset.js","  Cache-Control: no-store, no-cache, must-revalidate, max-age=0","  Service-Worker-Allowed: /",
    "/sw-v327-reset.js","  Cache-Control: no-store, no-cache, must-revalidate, max-age=0","  Service-Worker-Allowed: /",
    "/sw-v326-reset.js","  Cache-Control: no-store, no-cache, must-revalidate, max-age=0","  Service-Worker-Allowed: /",
    "/sw-v325-reset.js","  Cache-Control: no-store, no-cache, must-revalidate, max-age=0","  Service-Worker-Allowed: /",
    "/sw-v324-reset.js","  Cache-Control: no-store, no-cache, must-revalidate, max-age=0","  Service-Worker-Allowed: /",
    "/sw-v323-reset.js","  Cache-Control: no-store, no-cache, must-revalidate, max-age=0","  Service-Worker-Allowed: /",
    "/sw-v322-reset.js","  Cache-Control: no-store, no-cache, must-revalidate, max-age=0","  Service-Worker-Allowed: /",
    "/sw-v321-reset.js","  Cache-Control: no-store, no-cache, must-revalidate, max-age=0","  Service-Worker-Allowed: /",
    "/sw-v320-reset.js","  Cache-Control: no-store, no-cache, must-revalidate, max-age=0","  Service-Worker-Allowed: /",
    "/sw-v319-reset.js","  Cache-Control: no-store, no-cache, must-revalidate, max-age=0","  Service-Worker-Allowed: /",
    "/sw-v318-reset.js","  Cache-Control: no-store, no-cache, must-revalidate, max-age=0","  Service-Worker-Allowed: /",
    f"/app-{BUILD_VERSION}.js","  Cache-Control: no-cache, must-revalidate",
    f"/arvexq-app-{BUILD_VERSION}.js","  Cache-Control: no-cache, must-revalidate",
    f"/styles-arvexq-{BUILD_VERSION}.css","  Cache-Control: no-cache, must-revalidate",
    "/morning/*","  Cache-Control: no-cache, must-revalidate",
    "/styles/*","  Cache-Control: no-cache, must-revalidate",
    "/research/*","  Cache-Control: no-cache, must-revalidate",
    "/racecards/*","  Cache-Control: no-cache, must-revalidate",
    "/betting/*","  Cache-Control: no-cache, must-revalidate",
    "/previous_ai_results.js","  Cache-Control: no-cache, must-revalidate",
    "/arvexq-racing-hero.webp","  Cache-Control: public, max-age=604800",
    "/arvexq-racing-detail.webp","  Cache-Control: public, max-age=604800",
    "/hero-horse.webp","  Cache-Control: public, max-age=604800",
    "/pace-preview.webp","  Cache-Control: public, max-age=604800",
    "/arvexq-logo.webp","  Cache-Control: public, max-age=604800",
]
(DIST / "_headers").write_text("\n".join(headers)+"\n",encoding="utf-8")

(DIST / "arvexq-touch-v175.png").write_bytes(base64.b64decode(binary_b64["ARVEXQ_TOUCH_ICON_180"]))
(DIST / "arvexq-icon-v175-192.png").write_bytes(base64.b64decode(icons["192"]))
(DIST / "arvexq-icon-v175-512.png").write_bytes(base64.b64decode(icons["512"]))
(DIST / "arvexq-icon-192.png").write_bytes(base64.b64decode(icons["192"]))
(DIST / "arvexq-icon-512.png").write_bytes(base64.b64decode(icons["512"]))
assets={"CINEMATIC_HERO_WEBP":"arvexq-racing-hero.webp","CINEMATIC_DETAIL_WEBP":"arvexq-racing-detail.webp","HERO_HORSE_WEBP":"hero-horse.webp","PACE_PREVIEW_WEBP":"pace-preview.webp","ARVEXQ_LOGO_WEBP":"arvexq-logo.webp"}
for var,filename in assets.items():
    if var in binary_b64:(DIST / filename).write_bytes(base64.b64decode(binary_b64[var]))

print(f"ARVEXQ static build complete: {DIST}")
print(f"BUILD: {BUILD_VERSION}")
print(f"Files: {len(list(DIST.rglob('*')))}")

# Daily pre-off selection archives are content-addressed by race date. Publish
# exact immutable JSON files without altering their race membership on refresh.
morning_dir = STATIC / "morning-picks"
if morning_dir.is_dir():
    target_dir = DIST / "morning-picks"
    target_dir.mkdir(exist_ok=True)
    for archive in morning_dir.glob("????-??-??.json"):
        shutil.copy2(archive, target_dir / archive.name)

# Lightweight, immutable factual racecard backup survives an unavailable D1.
racecard_dir = STATIC / "racecards"
if racecard_dir.is_dir():
    target_dir = DIST / "racecards"
    target_dir.mkdir(exist_ok=True)
    for archive in racecard_dir.glob("????-??-??.json"):
        shutil.copy2(archive, target_dir / archive.name)

# Losslessly archived existing race originals, independent of D1 availability.
if (STATIC / "saved-snapshots").is_dir():
    shutil.copytree(STATIC / "saved-snapshots", DIST / "saved-snapshots")

from scripts.arvexq_build_odds_sources import build_sources
build_sources(STATIC, DIST)
