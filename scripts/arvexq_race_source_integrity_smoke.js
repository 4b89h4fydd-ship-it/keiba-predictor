/* Legacy writer regression: one D1 display fetch, verified static first,
   compact racecard only on actual roster failure; never modify model scores. */
const assert=require('node:assert/strict');
const fs=require('node:fs');
const src=fs.readFileSync('arvexq/ui/static/app.js','utf8');
const start=src.indexOf('function openRace('),end=src.indexOf('\n}',start)+2;
assert(start>=0&&end>start,'missing openRace');
const open=src.slice(start,end);
assert(open.includes('hydrateStaticRacecardFirst(id,seq,initial)'));
assert(open.includes('fetchEdgeRace(id,true,2)'));
assert.equal((open.match(/fetchEdgeRace\(id,true/g)||[]).length,1);
assert.equal((open.match(/fetchRacecardOnly\(id\)/g)||[]).length,1);
assert(!open.includes('window.ARVEXQSavedSnapshot.available('),
  'legacy parallel saved snapshot fetch can overwrite authoritative D1');
assert(open.indexOf('fetchRacecardOnly(id)')>open.indexOf('if(entryDataAvailable(state.race))'),
  'racecard request must only run as a last resort');
assert(open.includes('seq!==state.detailSeq'),'never update after navigation');
assert(!src.includes('function homePickAlert('),'obsolete alert helper removed');
assert.equal((src.match(/function specialForecastRaceCandidates\(/g)||[]).length,1);
const workflow=fs.readFileSync('.github/workflows/arvexq-race-open-repair.yml','utf8');
assert(workflow.includes('contents: read'));
assert(!workflow.includes('git push')&&!workflow.includes('Apply repair'));
assert(!src.includes('function smartHomeHub('),'old unused home removed');
assert(src.includes('evictRetiredRaceCaches();'),'obsolete device race caches must be evicted');
assert(!src.includes('saved-snapshot-restored'),'legacy saved snapshot live restore removed');
assert(!fs.existsSync('scripts/arvexq_patch_race_open_reliability.py'));
const model=fs.readFileSync('arvexq/prediction/factor_model.py','utf8');
assert(model.includes('SCORE_WEIGHTS = {"trueRun": .45, "pure": .35, "sectional": .20}'),'one authoritative 45/35/20 ranking');
assert(!fs.existsSync('arvexq/prediction/honmei_gate.py'),'retired parallel axis scorer must be deleted');
// Regression: the active horse homepage still needs a read-only pick-count helper.
// An old-home cleanup previously removed this shared function, crashing on launch.
const countStart=src.indexOf('function homePickCounts(');
const countEnd=src.indexOf('\n}',countStart)+2;
assert(countStart>=0&&countEnd>countStart,'homePickCounts must exist for app boot');
const countFunction=src.slice(countStart,countEnd);
assert(src.includes('function renderHome(){')&&
  src.slice(src.indexOf('function renderHome(){'),src.indexOf('function volatilityBadge(')).includes("homePickCounts('selected')"),
  'current home must be able to read its selection counts');
const counts=new Function('selectedRaceCandidates','specialForecastRaceCandidates',
  countFunction+'; return homePickCounts;')(
    c=>c==='中央'?[{id:'a'},{id:'b'}]:[{id:'c'}],
    ()=>[{circuit:'中央'},{circuit:'地方'},{circuit:'地方'}]);
assert.deepEqual(counts('selected'),{central:2,local:1});
assert.deepEqual(counts('special'),{central:1,local:2});
// Regression: previous home cleanup accidentally removed the actual runner
// renderer while leaving the two call sites intact. Execute its real HTML.
const rowStart=src.indexOf('function racecardEntryRow(');
const rowEnd=src.indexOf('function morningSavedMarkRows(',rowStart);
assert(rowStart>=0&&rowEnd>rowStart,'racecardEntryRow is required to show runners');
assert.equal((src.match(/function racecardEntryRow\(/g)||[]).length,1,'single renderer authority');
// The real page defines markRoleLabel in the same script as racecardEntryRow.
// Inject the production helper into this isolated renderer test, not a mock.
const roleStart=src.indexOf('function markRoleLabel(');
const roleEnd=src.indexOf('\n}',roleStart)+2;
assert(roleStart>=0&&roleEnd>roleStart,'production markRoleLabel helper is required');
const markRoleLabel=new Function(src.slice(roleStart,roleEnd)+';return markRoleLabel;')();
assert.equal(markRoleLabel({predMark:'◎'}),'◎【単】');
const renderRunner=new Function(
  'isScratchHorse','n','horseDisplayName','clamp',
  'currentBodyWeight','currentBodyWeightChange','referenceBodyWeight',
  'carriedWeightText','esc','racecardOddsHtml','racecardMarkDisplay',
  'honmeiA11yText','honmeiBadgeText','markRoleLabel',
  src.slice(rowStart,rowEnd)+';return racecardEntryRow;'
)(
  ()=>false, (x,d=0)=>Number.isFinite(Number(x))?Number(x):d,
  (_r,h)=>h.name, (x,lo,hi)=>Math.max(lo,Math.min(hi,x)),
  ()=>480, ()=>3, ()=>0, ()=>57, x=>String(x??''),
  ()=>'<span>3.2</span>',x=>String(x||'—'),()=>'',()=>'',
  markRoleLabel
);
const runnerHtml=renderRunner({id:'test'},{
  horseNumber:7,name:'サンプル号',frameNumber:4,sex:'牡',age:4,jockey:'騎手'
},{predMark:'◎',honmeiGrade:'A'});
assert.match(runnerHtml,/racecard-row/);
assert.match(runnerHtml,/サンプル号/);
assert.match(runnerHtml,/data-horse-open="7"/);
assert.match(runnerHtml,/data-ai-mark="◎"/);
assert.match(src,/function minimalRacecardPanel\(/);
assert.match(src,/function runnerStyleSection\(/);
console.log('ARVEXQ_SINGLE_SOURCE_RACE_OPEN_AND_PERSISTENT_ALERT_OK');

const home=fs.readFileSync('arvexq/ui/static/sports/unified-home.js','utf8');
const style=fs.readFileSync('arvexq/ui/static/sports/unified-home.css','utf8');
const root={};new Function('window',home)(root);
const actions=root.ARVEXQUnifiedHome.buttons();
assert.equal((actions.match(/class="arv-unified-alert"/g)||[]).length,2,'selected and special need !');
assert.match(style,/arv-unified-alert/);
