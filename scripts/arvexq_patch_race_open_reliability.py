#!/usr/bin/env python3
from pathlib import Path

PATH = Path('arvexq/ui/static/app.js')
text = PATH.read_text(encoding='utf-8')


def replace_function(src: str, name: str, replacement: str) -> str:
    marker = f'function {name}('
    start = src.find(marker)
    if start < 0:
        if replacement in src:
            return src
        raise SystemExit(f'{name}: function not found')
    brace = src.find('{', start)
    if brace < 0:
        raise SystemExit(f'{name}: opening brace not found')
    depth = 0
    quote = None
    escape = False
    i = brace
    while i < len(src):
        ch = src[i]
        if quote:
            if escape:
                escape = False
            elif ch == '\\':
                escape = True
            elif ch == quote:
                quote = None
        else:
            if ch in ('\"', "'", '`'):
                quote = ch
            elif ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    return src[:start] + replacement + src[i + 1:]
        i += 1
    raise SystemExit(f'{name}: closing brace not found')


COURSE_PROFILE = '''function courseProfile(r){
  r=r||{};
  return COURSE[r.track]||{lap:1400,straight:300,dir:-1,shape:"wide",turn:"右",firstTurn:300}
}'''

COURSE_STAGE = '''function courseStageFrac(r,st){
  r=r||{};
  var p=courseProfile(r);
  if(p.shape==="straight")return st===0?.05:(st===1?.67:.92);
  var laps=Math.max(.1,n(r.distance,1200)/p.lap),start=normFrac(.965-p.dir*(laps%1)),prog=st===0?.015:(st===1?.81:.965);
  return normFrac(start+p.dir*laps*prog)
}'''

RACE_READY = '''function raceDisplayCoreReady(d,row){
  if(!d)return false;
  var hs=(d.horses||[]).filter(function(h){return h&&n(h.horseNumber)>0}),fs=d.result&&d.result.finishers||[];
  if(!hs.length){
    return isFinal(d)&&fs.some(function(x){return x&&n(x.horseNumber)>0&&String(x.name||'').trim()})
  }
  var active=hs.filter(function(h){return !isScratchHorse(h)});
  if(!active.length)active=hs;
  var named=active.filter(function(h){return String(h.name||'').trim()}).length;
  // Rendering uses runner identity only. Secondary fields can continue syncing.
  // Prediction and bet locking keep their separate strict data-readiness checks.
  return named>=Math.min(active.length,Math.max(1,Math.ceil(active.length*.50)))
}'''

RENDER_RACE = '''function renderRace(){
  var r=applySummaryEnvironment(mergeResultHorseFields(state.race)),p=null,predictionError=null;
  state.race=r;
  try{
    p=predict(r);
    state.pred=p
  }catch(e){
    predictionError=e;
    state.pred=null;
    p={
      rows:(r.horses||[]).filter(function(h){return h&&n(h.horseNumber)>0}).map(function(h){return{
        horse:h,predMark:'',predRank:999,overallRaw:0,overallGrade:'C',winProbability:0,marketProbability:0,
        p1Probability:0,p2Probability:0,p3Probability:0,winnerDecisionProbability:0,winnerConsensusProbability:0,
        expected:'不明',pastStyle:'不明',styleSamples:0,rawFront:0,rawStalk:0,rawMid:0,rawClose:0,fade:0,
        frontStay:0,comeFromBehind:0,collapseBeneficiary:0,paceScore:0,posCons:0,latePower:0,coverage:0
      }}),
      scenarios:[],plans:{},plan:null,arrangement:{},coverage:0
    };
    // The racecard is a primary view and must never depend on AI completion.
    state.openPanel='entry'
  }
  if(!state.openPanel)state.openPanel='entry';
  var top=(p.scenarios||[]).slice().sort(function(a,b){return n(b.prob)-n(a.prob)})[0];
  if(!state.scenarioCode||!p.plans||!p.plans[state.scenarioCode])state.scenarioCode=top?top.code:null;
  if(state.subPage==='horse')return horseDetailPage(r,p);
  if(state.subPage==='bets')return betDetailPage(r,p);
  if(state.subPage==='pace-stage')return paceStagePage(r,p);
  var content='';
  try{
    content=detailTabs(r,p)
  }catch(e){
    predictionError=predictionError||e;
    state.openPanel='entry';
    content=minimalRacecardPanel(r)
  }
  if(predictionError&&content.indexOf('AI解析はバックグラウンド')<0){
    content='<div class="diagnosis-refresh-note busy" style="margin:7px 0">AI解析の一部を再取得中です。出走表の表示は継続します。</div>'+content
  }
  return '<div class="smart-shell">'+
    smartRaceTopBar(r)+
    '<main class="smart-main smart-race-page">'+
      smartRaceHead(r)+
      cinematicTabs(r)+
      '<div class="smart-race-content">'+content+'</div>'+ 
    '</main>'+ 
    cinematicFooter()+
  '</div>'
}'''

text = replace_function(text, 'courseProfile', COURSE_PROFILE)
text = replace_function(text, 'courseStageFrac', COURSE_STAGE)
text = replace_function(text, 'raceDisplayCoreReady', RACE_READY)
text = replace_function(text, 'renderRace', RENDER_RACE)

old_footer = "function cinematicFooter(){return '<footer class=\"cinematic-footer\"><b>ARVEXQ</b><span>ARTIFICIAL RACING INTELLIGENCE</span><small>TACTICAL ENGINE · BUILD v326</small></footer>'}"
new_footer = "function cinematicFooter(){return '<footer class=\"cinematic-footer\"><b>ARVEXQ</b><span>ARTIFICIAL RACING INTELLIGENCE</span><small>TACTICAL ENGINE · BUILD '+esc(window.ARVEXQ_BUILD||'v329')+'</small></footer>'}"
if old_footer in text:
    text = text.replace(old_footer, new_footer, 1)
elif new_footer not in text and 'BUILD v326</small></footer>' in text:
    text = text.replace('BUILD v326</small></footer>', "BUILD '+esc(window.ARVEXQ_BUILD||'v329')+'</small></footer>", 1)

required = [
    'function specialForecastRaceCandidates()',
    "String(r.track||'')==='高知'",
    'lockWindow=30',
    'n(rd.actualOdds,0)>=.65',
    'n(rd.bodyWeight,0)>=.70',
    'n(rd.environment,0)>=1',
    "plan.lockPolicy='v327-final-input-window-30m'",
    'window.ARVEXQ_BUILD="v329";',
    'function courseProfile(r){\n  r=r||{};',
    'function courseStageFrac(r,st){\n  r=r||{};',
    "if(state.subPage==='pace-stage')return paceStagePage(r,p);",
    'The racecard is a primary view and must never depend on AI completion.',
    'content=minimalRacecardPanel(r)',
]
missing = [x for x in required if x not in text]
if missing:
    raise SystemExit('race-open patch invariant failure: ' + repr(missing))

fn_start = text.find('function raceDisplayCoreReady(')
fn_end = text.find('\n}', fn_start) + 2
ready_block = text[fn_start:fn_end]
for forbidden in ('h.carriedWeight', 'h.jockey', '.fieldSize'):
    if forbidden in ready_block:
        raise SystemExit(f'race display still contains strict secondary gate {forbidden}')

for name in ('courseProfile', 'courseStageFrac'):
    start = text.find(f'function {name}(')
    end = text.find('\n}', start) + 2
    block = text[start:end]
    if 'r=r||{};' not in block:
        raise SystemExit(f'{name}: missing null guard')

render_start = text.find('function renderRace()')
render_end = text.find('\n}', render_start) + 2
render_block = text[render_start:render_end]
if 'try{\n    p=predict(r);' not in render_block or "state.openPanel='entry'" not in render_block:
    raise SystemExit('renderRace: prediction isolation missing')
if "if(state.subPage==='pace-stage')return paceStagePage(r,p);" not in render_block:
    raise SystemExit('renderRace: pace-stage subpage routing missing')
if 'content=minimalRacecardPanel(r)' not in render_block:
    raise SystemExit('renderRace: safe racecard fallback missing')

PATH.write_text(text, encoding='utf-8')
print('ARVEXQ race-open reliability patched: racecard independent from prediction failures + Safari guards')
