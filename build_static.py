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
    # Normal assignments such as CSS = r"""..."""
    if isinstance(node, ast.Assign) and len(node.targets) == 1:
        target = node.targets[0]
        if not isinstance(target, ast.Name):
            continue

        name = target.id
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

    # app.py extends CSS many times with CSS += r"""...""".
    # The static build must reproduce those additions in source order.
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
        raise RuntimeError(f"{required} not found in app.py")

BUILD_VERSION = "v173"
js = re.sub(r"BUILD v\d+", f"BUILD {BUILD_VERSION}", strings["JS"])
js = re.sub(r'(arvexq-sw-reload"\)!==")v[^"\n]+("\))', r'\1'+BUILD_VERSION+r'-edge-only\2', js)
js = js.replace('"v133-edge-only"', f'"{BUILD_VERSION}-edge-only"')
# v148: the SW script URL itself changes, forcing Safari/PWA to check a new worker.
js = js.replace('navigator.serviceWorker.register("/sw.js",{scope:"/"})',
                f'navigator.serviceWorker.register("/sw-{BUILD_VERSION}.js",{{scope:"/"}})')
# Expose the running build without changing normal UI.
js = f'window.ARVEXQ_BUILD="{BUILD_VERSION}";\n' + js

# Cloudflare summary rows carry raceStatus rather than a nested result object.
# Venue/home rows must still switch to "確定" immediately.
js = js.replace(
    'function isFinal(r){return !!(r&&r.result&&(r.result.status==="確定"||(r.result.finishers||[]).length))}',
    'function isFinal(r){return !!(r&&((r.result&&(r.result.status==="確定"||(r.result.finishers||[]).length))||r.raceStatus==="確定"))}'
)

# When a venue refresh receives a final detail, propagate the result back into
# the summary row so the list changes to 確定 without reopening the whole day.
js = js.replace(
    "if(r&&d.volatility){\n"
    "      var before=JSON.stringify(r.volatility||null),after=JSON.stringify(d.volatility);\n"
    "      if(before!==after){r.volatility=d.volatility;changed=true}\n"
    "    }",
    "if(r&&d.volatility){\n"
    "      var before=JSON.stringify(r.volatility||null),after=JSON.stringify(d.volatility);\n"
    "      if(before!==after){r.volatility=d.volatility;changed=true}\n"
    "    }\n"
    "    if(r&&d.result&&((d.result.finishers||[]).length||d.result.status==='確定')){\n"
    "      r.result=d.result;r.raceStatus='確定';changed=true\n"
    "    }"
)

# On today's venue screen keep checking races that have already started but
# are not yet marked final, even when volatility/diagnosis is already complete.
js = js.replace(
    "var pending=state.races.some(function(x){return x.track===state.track&&x.circuit===state.circuit&&!(x.volatility&&x.volatility.ready)});",
    "var pending=state.races.some(function(x){return x.track===state.track&&x.circuit===state.circuit&&"
    "(!(x.volatility&&x.volatility.ready)||(state.date===today()&&mins(x.startTime)<=nowMins()-3&&!isFinal(x)))});"
)



# Keep roughly one week of dates directly reachable without opening the calendar.
js = js.replace(
    "function dateStrip(){var center=new Date(state.date+'T12:00:00'),out='';for(var i=-1;i<=3;i++){",
    "function dateStrip(){var center=new Date(state.date+'T12:00:00'),out='';for(var i=-7;i<=2;i++){",
)

# Keep frontend prediction metadata aligned with the current server diagnosis engine.
js = js.replace(
    "engineVersion:'arvexq-commercial-2026.09-v2'",
    "engineVersion:'arvexq-commercial-2026.09-v9'",
)

# If a race has started but the venue row is not final yet, bypass the in-memory
# snapshot so the list actually sees the newest D1 result instead of looping on stale cache.
js = js.replace(
    "return fetchEdgeRace(row.id,!(row.volatility&&row.volatility.ready))",
    "var needLiveResult=requestedDate===today()&&mins(row.startTime)<=nowMins()-3&&!isFinal(row);\n"
    "    return fetchEdgeRace(row.id,needLiveResult||!(row.volatility&&row.volatility.ready))",
)
js = js.replace(
    "return fetchEdgeRace(row.id)\n      .then(function(d){",
    "var needLiveResult=requestedDate===today()&&mins(row.startTime)<=nowMins()-3&&!isFinal(row);\n"
    "    return fetchEdgeRace(row.id,needLiveResult)\n      .then(function(d){",
)

# v141 × navigation hierarchy:
# TOP venue list -> selected venue all races -> race detail.
# × always moves exactly one level back.
js = js.replace(
    'class="smart-back" data-action="home"',
    'class="smart-back" data-action="back"',
)

gb_start = js.find("function goBack(){")
gb_end = js.find("\n}\nvar navigationRestoring", gb_start)
if gb_start < 0 or gb_end < 0:
    raise RuntimeError("goBack block not found in app JS")
gb_end += 2

new_go_back = """function goBack(){
    if(!canGoBack())return;
    if(state.horseModalNo){closeHorseModal();return}
    ++state.detailSeq;
    if(state.historyTimer){clearTimeout(state.historyTimer);state.historyTimer=null}
    if(state.collectTimer){clearTimeout(state.collectTimer);state.collectTimer=null}
    state.collectingHorse=null;state.error=null;state.pred=null;state.scenarioCode=null;state.paceStage=0;

    if(state.raceLoading||state.race){
        if(state.raceStack.length){
            // A past-race detail returns to the race detail that opened it.
            state.raceLoading=null;
            state.race=state.raceStack.pop();
            state.picker=false;
            if(state.race&&state.race.track)state.track=state.race.track
        }else{
            // A normal race detail returns to this venue's full race list.
            var keepTrack=state.track||(state.race&&state.race.track)||"";
            state.raceLoading=null;
            state.race=null;
            state.picker=false;
            state.track=keepTrack||null
        }
    }else if(state.picker){
        state.picker=false;
        state.track=null
    }else if(state.track){
        // Venue full race list returns to the top venue list.
        state.track=null;
        state.picker=false
    }

    // Do not use browser history for the × button; keep app hierarchy deterministic.
    routeKey=null;
    render();
    window.scrollTo(0,0)
}"""
js = js[:gb_start] + new_go_back + js[gb_end:]

# Cloudflare/D1 first. Remove old same-origin Render/manual fallbacks.
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

# Old installed iPhone PWAs may still launch with ?pwa=1.
# Remove it from the browser history URL once the UI state is restored.
js = js.replace(
    "if(view.picker)u.searchParams.set('picker','1');else u.searchParams.delete('picker');var prior=window.history.state||{}",
    "if(view.picker)u.searchParams.set('picker','1');else u.searchParams.delete('picker');"
    "u.searchParams.delete('pwa');var prior=window.history.state||{}",
)

# Do not let a generic Safari 'Script error.' wipe a screen that already rendered.
old_error = (
    "window.onerror=function(msg){if(app)app.innerHTML='<div class=\"notice\" "
    "style=\"margin:20px\">表示エラー：'+esc(msg)+'<br><button onclick=\"location.reload()\">"
    "再読み込み</button></div>';return false};"
)
new_error = (
    "var arvexqBootPainted=false;"
    "window.onerror=function(msg,src,line,col,err){"
    "try{console.error('ARVEXQ runtime error',msg,src,line,col,err||'')}catch(_e){};"
    "try{if(app&&!arvexqBootPainted&&app.querySelector&&app.querySelector('.boot')){"
    "var where=(src?String(src).split('/').pop():'')+(line?':'+line:'');"
    "app.innerHTML='<div class=\"notice\" style=\"margin:20px\">起動エラー：'+"
    "esc(msg||'不明なエラー')+(where?'<br><small>'+esc(where)+'</small>':'')+"
    "'<br><button onclick=\"location.reload()\">再読み込み</button></div>'}}catch(_e){};"
    "return false};"
)
if old_error in js:
    js = js.replace(old_error, new_error, 1)

old_boot = (
    "installNavigation();installEdgeBack();installPwaCache();restoreLocation();setTimeout(load,0);"
)
new_boot = (
    "try{installNavigation()}catch(e){try{console.error(e)}catch(_e){}};"
    "try{installEdgeBack()}catch(e){try{console.error(e)}catch(_e){}};"
    "try{installPwaCache()}catch(e){try{console.error(e)}catch(_e){}};"
    "try{restoreLocation()}catch(e){try{console.error(e)}catch(_e){}};"
    "setTimeout(function(){try{load();arvexqBootPainted=true}catch(e){try{console.error(e)}catch(_e){}}},0);"
    "setTimeout(function(){arvexqBootPainted=true},3000);"
)
if old_boot in js:
    js = js.replace(old_boot, new_boot, 1)

remaining = [
    line.strip()
    for line in js.splitlines()
    if "fetch('/api/v1/" in line or 'fetch("/api/v1/' in line
]
if remaining:
    raise RuntimeError(
        "Render API fetch remains in static build:\n" + "\n".join(remaining[:20])
    )

index_html = strings["INDEX"].replace(
    '<link rel="stylesheet" href="/styles-arvexq-v130.css">',
    '<style>' + strings["CSS"] + '</style>'
)

# More reliable standalone detection on iPhone and other installed PWAs.
index_html = index_html.replace(
    '<script>try{if(window.navigator.standalone===true)document.documentElement.classList.add("pwa-standalone")}catch(e){}</script>',
    '<script>try{var s=window.navigator.standalone===true||'
    '(window.matchMedia&&window.matchMedia("(display-mode: standalone)").matches);'
    'if(s)document.documentElement.classList.add("pwa-standalone")}catch(e){}</script>'
)

# v148: use a brand-new asset path so an old iPhone/PWA service worker cannot
# answer with a cached app-v146/app-v147 bundle. Regex catches every historical
# app-vNNN.js reference without maintaining a fragile hand-written list.
JS_ASSET = f"/arvexq-app-{BUILD_VERSION}.js"
index_html = re.sub(r'/app-v\d+(?:-[^"\']+)?\.js', JS_ASSET, index_html)

(DIST / "index.html").write_text(index_html, encoding="utf-8")
(DIST / "404.html").write_text(index_html, encoding="utf-8")
for route in ("venue", "race"):
    (DIST / route).mkdir()
    (DIST / route / "index.html").write_text(index_html, encoding="utf-8")

(DIST / "build-version.txt").write_text(BUILD_VERSION+"\n", encoding="utf-8")

(DIST / "_redirects").write_text(
    "/venue /index.html 200\n/race /index.html 200\n",
    encoding="utf-8",
)

(DIST / "styles-arvexq-v130.css").write_text(strings["CSS"], encoding="utf-8")
(DIST / f"arvexq-app-{BUILD_VERSION}.js").write_text(js, encoding="utf-8")
# Keep the conventional filename too for direct/debug access.
(DIST / f"app-{BUILD_VERSION}.js").write_text(js, encoding="utf-8")

# Compatibility copies are intentional.
# A stale home-screen HTML/SW that asks for v137/v136/v133 still receives JS,
# not an SPA HTML fallback, while v146 takes control.
for compat in ("v147", "v146", "v145", "v141", "v140", "v139", "v138", "v137", "v136", "v133"):
    (DIST / f"app-{compat}.js").write_text(js, encoding="utf-8")

manifest = strings["MANIFEST"]
(DIST / "manifest-arvexq-v173.webmanifest").write_text(manifest, encoding="utf-8")
(DIST / "manifest-arvexq-v130.webmanifest").write_text(manifest, encoding="utf-8")

# iOS/Safari rejects a redirected Response when it is returned by a Service
# Worker navigation handler ("Response served by service worker has redirections").
# Always fetch /index.html directly and clone it into a fresh Response, which
# strips redirect metadata before it is returned to the browser.
sw = f'''const CACHE="arvexq-shell-{BUILD_VERSION}-safe-navigation";
const STATIC=[
  "/index.html",
  "/arvexq-app-{BUILD_VERSION}.js",
  "/manifest-arvexq-v173.webmanifest",
  "/arvexq-icon-v173-192.png",
  "/arvexq-icon-v173-512.png",
  "/arvexq-racing-hero.webp"
];

async function cleanResponse(r){{
  const body=await r.arrayBuffer();
  return new Response(body,{{
    status:r.status,
    statusText:r.statusText,
    headers:new Headers(r.headers)
  }});
}}

self.addEventListener("install",event=>{{
  event.waitUntil(
    caches.open(CACHE)
      .then(async cache=>{{
        for(const url of STATIC){{
          try{{
            const r=await fetch(url,{{cache:"reload",redirect:"follow"}});
            if(r&&r.ok)await cache.put(url,await cleanResponse(r));
          }}catch(_e){{}}
        }}
      }})
      .then(()=>self.skipWaiting())
  );
}});

self.addEventListener("activate",event=>{{
  event.waitUntil(
    caches.keys()
      .then(keys=>Promise.all(keys.filter(k=>k!==CACHE).map(k=>caches.delete(k))))
      .then(()=>self.clients.claim())
  );
}});

self.addEventListener("fetch",event=>{{
  const req=event.request;
  if(req.method!=="GET")return;
  const url=new URL(req.url);
  if(url.origin!==self.location.origin)return;
  if(url.pathname.startsWith("/api/"))return;

  if(req.mode==="navigate"){{
    event.respondWith((async()=>{{
      const cache=await caches.open(CACHE);
      try{{
        const r=await fetch("/index.html?sw="+Date.now(),{{
          cache:"no-store",
          redirect:"follow"
        }});
        if(!r||!r.ok)throw new Error("navigation "+(r&&r.status));
        const clean=await cleanResponse(r);
        await cache.put("/index.html",clean.clone());
        return clean;
      }}catch(_e){{
        return (await cache.match("/index.html")) ||
          new Response("通信状態を確認して再読み込みしてください",{{
            status:503,
            headers:{{"Content-Type":"text/plain; charset=utf-8"}}
          }});
      }}
    }})());
    return;
  }}

  if(STATIC.includes(url.pathname)){{
    event.respondWith((async()=>{{
      const cache=await caches.open(CACHE);
      const cached=await cache.match(url.pathname);
      if(cached)return cached;
      const r=await fetch(req,{{cache:"reload",redirect:"follow"}});
      if(!r||!r.ok)return r;
      const clean=await cleanResponse(r);
      await cache.put(url.pathname,clean.clone());
      return clean;
    }})());
  }}
}});
'''
(DIST / "sw.js").write_text(sw, encoding="utf-8")
(DIST / f"sw-{BUILD_VERSION}.js").write_text(sw, encoding="utf-8")

(DIST / "_headers").write_text(
    "/\n"
    "  Cache-Control: no-store\n"
    "/index.html\n"
    "  Cache-Control: no-store\n"
    "/404.html\n"
    "  Cache-Control: no-store\n"
    f"/arvexq-app-{BUILD_VERSION}.js\n"
    "  Cache-Control: no-store\n"
    "/app-v145.js\n"
    "  Cache-Control: no-store\n"
    "/app-v140.js\n"
    "  Cache-Control: no-store\n"
    "/app-v139.js\n"
    "  Cache-Control: no-store\n"
    "/app-v138.js\n"
    "  Cache-Control: no-store\n"
    "/app-v137.js\n"
    "  Cache-Control: no-store\n"
    "/app-v136.js\n"
    "  Cache-Control: no-store\n"
    "/app-v133.js\n"
    "  Cache-Control: no-store\n"
    "/manifest-arvexq-v173.webmanifest\n"
    "  Cache-Control: no-store\n"
    "/arvexq-touch-v173.png\n"
    "  Cache-Control: no-store\n"
    "/sw.js\n"
    "  Cache-Control: no-store\n"
    "  Service-Worker-Allowed: /\n"
    f"/sw-{BUILD_VERSION}.js\n"
    "  Cache-Control: no-store\n"
    "  Service-Worker-Allowed: /\n",
    encoding="utf-8",
)

if not icons:
    raise RuntimeError("ARVEXQ_ICONS not found")
if "ARVEXQ_TOUCH_ICON_180" not in binary_b64:
    raise RuntimeError("ARVEXQ_TOUCH_ICON_180 not found")

(DIST / "arvexq-touch-v173.png").write_bytes(base64.b64decode(binary_b64["ARVEXQ_TOUCH_ICON_180"]))
(DIST / "arvexq-icon-v173-192.png").write_bytes(base64.b64decode(icons["192"]))
(DIST / "arvexq-icon-v173-512.png").write_bytes(base64.b64decode(icons["512"]))
# Compatibility aliases for older installed shells; the HTML/manifest use v173 URLs.
(DIST / "arvexq-icon-192.png").write_bytes(base64.b64decode(icons["192"]))
(DIST / "arvexq-icon-512.png").write_bytes(base64.b64decode(icons["512"]))

assets = {
    "CINEMATIC_HERO_WEBP": "arvexq-racing-hero.webp",
    "CINEMATIC_DETAIL_WEBP": "arvexq-racing-detail.webp",
    "HERO_HORSE_WEBP": "hero-horse.webp",
    "ARVEXQ_LOGO_WEBP": "arvexq-logo.webp",
    "PACE_PREVIEW_WEBP": "pace-preview.webp",
}

for variable, filename in assets.items():
    if variable not in binary_b64:
        raise RuntimeError(f"{variable} not found in app.py")
    (DIST / filename).write_bytes(base64.b64decode(binary_b64[variable]))

print(f"ARVEXQ static build complete: {DIST}")
print(f"BUILD: {BUILD_VERSION}")
print(f"Files: {len(list(DIST.rglob('*')))}")
