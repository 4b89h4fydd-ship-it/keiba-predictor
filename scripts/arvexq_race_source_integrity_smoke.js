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
const full=fs.readFileSync('arvexq/prediction/honmei_gate.py','utf8');
assert(full.includes('.32 * recent_score'),'must preserve existing scoring weights');
console.log('ARVEXQ_SINGLE_SOURCE_RACE_OPEN_AND_PERSISTENT_ALERT_OK');

const home=fs.readFileSync('arvexq/ui/static/sports/unified-home.js','utf8');
const style=fs.readFileSync('arvexq/ui/static/sports/unified-home.css','utf8');
const root={};new Function('window',home)(root);
const actions=root.ARVEXQUnifiedHome.buttons();
assert.equal((actions.match(/class="arv-unified-alert"/g)||[]).length,2,'selected and special need !');
assert.match(style,/arv-unified-alert/);
