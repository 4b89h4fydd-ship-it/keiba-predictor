from pathlib import Path
import ast
import base64
import json
import re
import shutil

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "app.py"
DIST = ROOT / "dist"
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

# Ability-first prediction core.
# No hand-picked 40%/42% style weights. Each independent evidence axis gets one vote.
# Missing evidence is skipped rather than replaced with a neutral score. Pace is only the last tie-break.
ABILITY_FIRST_JS = r'''
/* ARVEXQ ability-first evidence ranker — injected by build_static.py */
function arvexqMedian(vals){
  var a=(vals||[]).filter(function(v){return v!=null&&isFinite(Number(v))}).map(Number).sort(function(x,y){return x-y});
  if(!a.length)return null;var m=Math.floor(a.length/2);return a.length%2?a[m]:(a[m-1]+a[m])/2
}
function arvexqAvg(vals){
  var a=(vals||[]).filter(function(v){return v!=null&&isFinite(Number(v))}).map(Number);
  if(!a.length)return null;var s=0;for(var i=0;i<a.length;i++)s+=a[i];return s/a.length
}
function arvexqRunKey(rr){
  rr=rr||{};return [rr.date||'',rr.track||'',n(rr.raceNumber,0),n(rr.distance,0),String(rr.title||'').trim()].join('|')
}
function arvexqRuns(h){
  var raw=(h&&h.allPastRuns&&h.allPastRuns.length?h.allPastRuns:(h&&h.recentRaces||[])),out=[],seen={};
  for(var i=0;i<raw.length;i++){
    var rr=raw[i]||{},k=arvexqRunKey(rr);
    if(seen[k])continue;seen[k]=1;out.push(rr)
  }
  out.sort(function(a,b){return String(b.date||'').localeCompare(String(a.date||''))});
  return out
}
function arvexqFinishValues(runs){
  var out=[];for(var i=0;i<(runs||[]).length;i++){
    var rr=runs[i]||{},f=n(rr.finish,0);if(!f)continue;
    var q=runFinishQuality(rr);if(q!=null&&isFinite(Number(q)))out.push(Number(q))
  }return out
}
function arvexqFilteredQuality(runs,fn){
  var a=[];for(var i=0;i<runs.length;i++)if(fn(runs[i])){var q=runFinishQuality(runs[i]);if(q!=null&&isFinite(Number(q)))a.push(Number(q))}
  return a.length?arvexqMedian(a):null
}
function arvexqEvidence(x,r){
  var h=x.horse||{},runs=arvexqRuns(h),recent=runs.slice(0,5),rv=arvexqFinishValues(recent),allv=arvexqFinishValues(runs.slice(0,20));
  var sameDist=arvexqFilteredQuality(runs,function(rr){var d=Math.abs(n(rr.distance,0)-n(r.distance,0));return d<=100||(n(r.distance,0)>=1800&&d<=200)});
  var sameTrack=arvexqFilteredQuality(runs,function(rr){return String(rr.track||'')===String(r.track||'')});
  var sameCond=arvexqFilteredQuality(runs,function(rr){return sameCondition(rr.condition,r.condition)});
  var top3=[];for(var i=0;i<recent.length;i++){var f=n(recent[i].finish,0);if(f)top3.push(f<=3?1:0)}
  var timed=false;for(i=0;i<runs.length;i++)if(n(runs[i].timeSeconds,0)>0){timed=true;break}
  var levelRuns=0;for(i=0;i<runs.length;i++)if(n(r.racePrize1,0)>0&&n(runs[i].racePrize1,0)>=n(r.racePrize1,0)*.8)levelRuns++;
  var metrics={
    recent:rv.length?arvexqMedian(rv):null,
    peak:allv.length?Math.max.apply(null,allv):null,
    speed:timed?n(x.speedScore,null):null,
    level:levelRuns?n(x.levelFit,null):null,
    distance:sameDist,
    track:sameTrack,
    condition:sameCond,
    consistency:top3.length?arvexqAvg(top3):null,
    proven:n(h.prizeMoneyAtRace,0)>0?n(x.prizeScore,null):null
  };
  var available=0;Object.keys(metrics).forEach(function(k){if(metrics[k]!=null&&isFinite(Number(metrics[k])))available++});
  var sources=1,ds=(r&&r.dataSources||[]);if(ds.length)sources=Math.max(sources,ds.length);if(h.smartRc&&Object.keys(h.smartRc).length)sources=Math.max(sources,2);if(h.extraSources)sources+=Object.keys(h.extraSources).length;
  return{metrics:metrics,available:available,sources:sources,runs:runs.length}
}
function arvexqCompareMetric(a,b,k){
  var av=a.metrics[k],bv=b.metrics[k];if(av==null||bv==null||!isFinite(Number(av))||!isFinite(Number(bv)))return 0;
  var d=Number(av)-Number(bv);if(Math.abs(d)<.015)return 0;return d>0?1:-1
}
function arvexqEvidenceRank(r,rows){
  var keys=['recent','speed','level','distance','track','condition','consistency','peak','proven'],i,j,k;
  for(i=0;i<rows.length;i++){
    rows[i].abilityEvidence=arvexqEvidence(rows[i],r);rows[i].abilityPairWins=0;rows[i].abilityPairTies=0;rows[i].abilityVoteMargin=0;rows[i].abilityComparisons=0
  }
  for(i=0;i<rows.length;i++)for(j=i+1;j<rows.length;j++){
    var a=rows[i],b=rows[j],va=0,vb=0,cmp=0;
    for(k=0;k<keys.length;k++){
      var c=arvexqCompareMetric(a.abilityEvidence,b.abilityEvidence,keys[k]);if(!c)continue;cmp++;if(c>0)va++;else vb++
    }
    if(!cmp)continue;
    a.abilityComparisons+=cmp;b.abilityComparisons+=cmp;a.abilityVoteMargin+=va-vb;b.abilityVoteMargin+=vb-va;
    if(va>vb)a.abilityPairWins++;else if(vb>va)b.abilityPairWins++;else{a.abilityPairTies++;b.abilityPairTies++}
  }
  var denom=Math.max(1,rows.length-1);
  rows.forEach(function(x){x.abilityEvidenceScore=Math.round(((x.abilityPairWins+x.abilityPairTies*.5)/denom)*100)});
  var sorted=rows.slice().sort(function(a,b){
    return b.abilityPairWins-a.abilityPairWins||b.abilityVoteMargin-a.abilityVoteMargin||b.abilityEvidence.available-a.abilityEvidence.available||
      n((b.abilityEvidence.metrics||{}).speed,-1)-n((a.abilityEvidence.metrics||{}).speed,-1)||
      n((b.abilityEvidence.metrics||{}).recent,-1)-n((a.abilityEvidence.metrics||{}).recent,-1)||
      n((b.abilityEvidence.metrics||{}).level,-1)-n((a.abilityEvidence.metrics||{}).level,-1)||
      Math.max(n(b.frontStay),n(b.comeFromBehind))-Math.max(n(a.frontStay),n(a.comeFromBehind))||
      n(a.horse.horseNumber)-n(b.horse.horseNumber)
  });
  var m=sorted.length;
  sorted.forEach(function(x,idx){
    x.abilityEvidenceRank=idx+1;x.overallScore=x.abilityEvidenceScore;x.overallRaw=x.abilityEvidenceScore/100;
    x.overallGrade=idx===0?'S':(idx<Math.max(2,Math.ceil(m*.30))?'A':(idx<Math.ceil(m*.70)?'B':'C'));
    var e=x.abilityEvidence.metrics||{},reasons=['能力・実績比較 '+(idx+1)+'位'];
    if(e.recent!=null&&e.recent>=.65)reasons.push('近走内容');
    if(e.speed!=null&&e.speed>=.60)reasons.push('実走速度');
    if(e.level!=null&&e.level>=.58)reasons.push('相手レベル');
    if(e.distance!=null&&e.distance>=.60)reasons.push('同距離実績');
    if(e.track!=null&&e.track>=.60)reasons.push('同場実績');
    if(e.condition!=null&&e.condition>=.60)reasons.push('馬場実績');
    if(e.consistency!=null&&e.consistency>=.60)reasons.push('安定性');
    if(x.abilityEvidence.sources>=2)reasons.push('複数ソース照合');
    x.overallReasons=reasons.slice(0,6)
  });
  return sorted
}
function arvexqAssignAbilityGrades(r,rows){arvexqEvidenceRank(r,rows)}
assignOverallGradesCentral=function(r,rows,suit,pressure){arvexqAssignAbilityGrades(r,rows)};
assignOverallGradesNar=function(r,rows,suit,pressure){arvexqAssignAbilityGrades(r,rows)};
assignPredictionMarks=function(rows,r){
  var sorted=rows.slice().sort(function(a,b){
    return n(a.abilityEvidenceRank,999)-n(b.abilityEvidenceRank,999)||n(b.abilityEvidenceScore)-n(a.abilityEvidenceScore)||
      n((b.abilityEvidence&&b.abilityEvidence.metrics||{}).speed,-1)-n((a.abilityEvidence&&a.abilityEvidence.metrics||{}).speed,-1)||
      n(a.horse.horseNumber)-n(b.horse.horseNumber)
  });
  var base=['◎','○','▲','☆','△'],i;
  for(i=0;i<sorted.length;i++){sorted[i].predRank=i+1;sorted[i].predMark=i<5?base[i]:'';sorted[i].attentionReason=''}
  if(!sorted.length)return;
  var fifth=sorted.length>=5?n(sorted[4].abilityEvidenceScore):0,c=[];
  for(i=5;i<sorted.length;i++){
    var x=sorted[i],ev=x.abilityEvidence||{available:0},gap=Math.max(0,fifth-n(x.abilityEvidenceScore));
    if(ev.available>=5&&gap<=10)c.push(x)
  }
  c.slice(0,2).forEach(function(x){x.predMark='注';x.attentionReason='能力・実績比較で上位と僅差'})
};
'''


def _inject_before_iife_close(script: str, patch: str) -> str:
    marker = "})();"
    pos = script.rfind(marker)
    if pos < 0:
        raise RuntimeError("ARVEXQ JS IIFE closing marker not found")
    return script[:pos] + "\n" + patch + "\n" + script[pos:]


js = _inject_before_iife_close(js, ABILITY_FIRST_JS)

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

compat_css = ("v321","v320","v319","v318","v317","v316","v315","v314","v313","v312","v308","v307","v306","v305","v303","v130")
compat_app = ("v321","v320","v319","v318","v317","v316","v315","v314","v313","v312","v308","v307","v306","v305","v303","v147","v146","v145","v141","v140","v139","v138","v137","v136","v133")
compat_arvexq = ("v321","v320","v319","v318","v317","v316","v315","v314","v313","v312","v308","v307","v306","v305","v303")
for name in ("manifest-arvexq-v175.webmanifest","manifest-arvexq-v173.webmanifest","manifest-arvexq-v130.webmanifest"):
    (DIST / name).write_text(manifest, encoding="utf-8")
(DIST / "sw.js").write_text(sw, encoding="utf-8")
(DIST / f"sw-{BUILD_VERSION}-reset.js").write_text(sw, encoding="utf-8")
for legacy_sw in ("v321", "v320", "v319", "v318"):
    (DIST / f"sw-{legacy_sw}-reset.js").write_text(sw, encoding="utf-8")

(DIST / "build-version.txt").write_text(BUILD_VERSION + "\n", encoding="utf-8")
model_version = strings.get("AI_EVALUATION_VERSION", "").removeprefix("evidence-")
(DIST / "version.json").write_text(json.dumps({"build":BUILD_VERSION,"shell":"ability-first-evidence","model":model_version},ensure_ascii=False,separators=(",",":"))+"\n",encoding="utf-8")
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
    "/sw-v321-reset.js","  Cache-Control: no-store, no-cache, must-revalidate, max-age=0","  Service-Worker-Allowed: /",
    "/sw-v320-reset.js","  Cache-Control: no-store, no-cache, must-revalidate, max-age=0","  Service-Worker-Allowed: /",
    "/sw-v319-reset.js","  Cache-Control: no-store, no-cache, must-revalidate, max-age=0","  Service-Worker-Allowed: /",
    "/sw-v318-reset.js","  Cache-Control: no-store, no-cache, must-revalidate, max-age=0","  Service-Worker-Allowed: /",
    f"/app-{BUILD_VERSION}.js","  Cache-Control: public, max-age=31536000, immutable",
    f"/arvexq-app-{BUILD_VERSION}.js","  Cache-Control: public, max-age=31536000, immutable",
    f"/styles-arvexq-{BUILD_VERSION}.css","  Cache-Control: public, max-age=31536000, immutable",
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
