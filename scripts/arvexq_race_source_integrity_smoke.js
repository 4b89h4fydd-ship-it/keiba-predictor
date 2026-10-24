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
const model=fs.readFileSync('arvexq/prediction/observed_model.py','utf8');
assert(model.includes('clear_marks(detail)'), 'retired adapter clears old fields');
assert(!model.includes('sum(observations)'), 'old scoring implementation removed');
assert(!fs.existsSync('arvexq/prediction/factor_model.py'),'retired central three-factor scorer must be physically deleted');
assert(!fs.existsSync('arvexq/prediction/nar_model.py'),'duplicate local scorer must be physically deleted');
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
assert.equal(markRoleLabel({predMark:'◎'}),'◎ 本命');
const visibleStart=src.indexOf('function visiblePredictionMark(');
const visibleEnd=src.indexOf('function honmeiA11yText(',visibleStart);
assert(visibleStart>=0&&visibleEnd>visibleStart,'shared visible axis mark helper required');
const visiblePredictionMark=new Function('window','isScratchHorse','markRoleLabel',
  src.slice(visibleStart,visibleEnd)+'return visiblePredictionMark;')(require('./test_support/production_ui.cjs').window,()=>false,markRoleLabel);
const renderRunner=new Function(
  'isScratchHorse','n','horseDisplayName','clamp',
  'currentBodyWeight','currentBodyWeightChange','referenceBodyWeight',
  'carriedWeightText','esc','racecardOddsHtml','racecardMarkDisplay',
  'honmeiA11yText','honmeiBadgeText','markRoleLabel','visiblePredictionMark',
  src.slice(rowStart,rowEnd)+';return racecardEntryRow;'
)(
  ()=>false, (x,d=0)=>Number.isFinite(Number(x))?Number(x):d,
  (_r,h)=>h.name, (x,lo,hi)=>Math.max(lo,Math.min(hi,x)),
  ()=>480, ()=>3, ()=>0, ()=>57, x=>String(x??''),
  ()=>'<span>3.2</span>',x=>String(x||'—'),()=>'',()=>'',
  markRoleLabel,visiblePredictionMark
);
const runnerHtml=renderRunner({id:'test'},{
  horseNumber:7,name:'サンプル号',frameNumber:4,sex:'牡',age:4,jockey:'騎手'
},{predMark:'◎',honmeiGrade:'A'});
assert.match(runnerHtml,/racecard-row/);
assert.match(runnerHtml,/サンプル号/);
assert.match(runnerHtml,/data-horse-open="7"/);
assert.match(runnerHtml,/data-ai-mark=""/);
assert.match(src,/function minimalRacecardPanel\(/);
assert.match(src,/function runnerStyleSection\(/);
console.log('ARVEXQ_SINGLE_SOURCE_RACE_OPEN_AND_PERSISTENT_ALERT_OK');

const home=fs.readFileSync('arvexq/ui/static/sports/unified-home.js','utf8');
const style=fs.readFileSync('arvexq/ui/static/sports/unified-home.css','utf8');
const root={};new Function('window',home)(root);
const actions=root.ARVEXQUnifiedHome.buttons();
assert.equal((actions.match(/class="arv-unified-alert"/g)||[]).length,0,'no selected or special alert without a real race');
const counted=root.ARVEXQUnifiedHome.buttons('horse',{selected:{central:1,local:0},special:{central:0,local:1}});
assert.equal((counted.match(/class="arv-unified-alert"/g)||[]).length,2,'selected and special need ! when each has at least one race');
assert.match(style,/arv-unified-alert/);

// Regression against legacy D1 list and device cache resurrecting excluded Banei.
const excludedStart=src.indexOf('function isExcludedBanei(');
const excludedEnd=src.indexOf('\n}',excludedStart)+2;
const filterStart=src.indexOf('function activeVenueRaces(');
const filterEnd=src.indexOf('\n}',filterStart)+2;
assert(excludedStart>=0&&filterStart>excludedEnd);
const visible=new Function(src.slice(excludedStart,excludedEnd)+'\n'+
  src.slice(filterStart,filterEnd)+';return activeVenueRaces;')();
const all=[
 {id:'nar-2026-10-24-帯広ば-01',track:'帯広ば'},
 {id:'nar-2026-10-24-帯広-02',track:'帯広'},
 {id:'nar-2026-10-24-帯広ば-03',track:'大井'},
 {id:'nar-2026-10-24-佐賀-01',track:'佐賀'},
 {id:'jra-2026-10-24-京都-02',track:'京都'}
];
assert.deepEqual(visible(all).map(r=>r.track),['佐賀','京都']);
assert.deepEqual(all.map(r=>r.track),['帯広ば','帯広','大井','佐賀','京都']); // source untouched
assert.equal(all.length,5,'never modify archived data');
const loadStart=src.indexOf('function loadRaceCache(');
const loadEnd=src.indexOf('\nfunction saveRaceCache(',loadStart);
assert(src.slice(loadStart,loadEnd).includes('activeVenueRaces(x.rows)'),'device cache must filter Banei');
assert(open.includes('isExcludedBanei({id:id})'),'direct race navigation must reject Banei');
const mergedStart=src.indexOf('function mergeBootstrap(');
const mergedEnd=src.indexOf('\nfunction load(',mergedStart);
assert(src.slice(mergedStart,mergedEnd).includes('activeVenueRaces(body&&body.races)'));
assert(src.includes('rows=activeVenueRaces(rows);'),'live fallback must filter Banei');
console.log('APP_BANEI_EXCLUSION_CACHE_API_DIRECT_ROUTE_PASS');

// A deep-link to a removed venue must normalize back to the home, not show a
// blank venue or issue a forbidden retired-race request.
const restoreStart=src.indexOf('function restoreLocation(');
const restoreEnd=src.indexOf('\nfunction installNavigation(',restoreStart);
assert(src.slice(restoreStart,restoreEnd).includes("if(isExcludedBanei({id:id,track:u.searchParams.get('track')}))"));
console.log('BANEI_DEEP_LINK_REJECTED_PASS');
