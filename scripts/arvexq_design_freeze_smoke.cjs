// Visual freeze for the approved ARVEXQ layout while removing old calculation logic.
// Intentional layout changes require explicit user approval and an updated baseline.
'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const cp=require('node:child_process');
const root=path.resolve(__dirname,'..');
// A PR compares against its exact existing base, rather than silently accepting
// changes to the visual design or reverting subsequently approved main styles.
const baselineRef=process.env.ARVEXQ_LAYOUT_BASE_REF||'';
if(baselineRef)assert.match(baselineRef,/^[0-9a-f]{40}$/,'layout baseline must be an exact commit');
function baseText(name){return cp.execFileSync('git',['show',baselineRef+':'+name],{cwd:root,encoding:'utf8',maxBuffer:2000000})}
const MASK=(1n<<64n)-1n;
function fingerprint(text){
  let h=14695981039346656037n;
  for(let i=0;i<text.length;i++)h=((h^BigInt(text.charCodeAt(i)))*1099511628211n)&MASK;
  return h.toString(16).padStart(16,'0');
}
const styleBaseline={
  "arvexq/ui/static/styles.css": "924bf5a30829c3bb",
  "arvexq/ui/static/styles/legacy_v118_v221.css": "f257fd1e4159db60",
  "arvexq/ui/static/styles/race_v222_plus.css": "d0f3c5933ba41ef0",
  // Re-pinned 2026-11-16: user-directed netkeiba-form light colour
  // scheme (dark navy shells/rows -> light background, dark text,
  // dark-green headers) in the home/venue/race theme block.
  // Re-pinned 2026-11-17: user-directed pure-white ground (the cream
  // paper theme #f6f2e8/#f7f7f4 -> #ffffff, tan borders -> light gray)
  // on the main screens.
  "arvexq/ui/static/sports/unified-home.css": "bc2daad4a4fd4c73",
  "arvexq/ui/static/sports/all-races.css": "b19226ee0bf5f854",
  "arvexq/ui/static/sports/pull-refresh.css": "498df97b7b5627bb",
  "arvexq/ui/static/research/research_view.css": "702cfda2ceefabd8",
  "arvexq/ui/static/betting/bet_ui.css": "ef2cb6dbeafbfef3"
};
for(const [name,expected] of Object.entries(styleBaseline)){
  const actual=fingerprint(fs.readFileSync(path.join(root,name),'utf8'));
  assert.equal(actual,baselineRef?fingerprint(baseText(name)):expected,'DO_NOT_CHANGE_ARVEXQ_CSS_LAYOUT: '+name);
}
const src=fs.readFileSync(path.join(root,'arvexq/ui/static/app.js'),'utf8');
function functionBody(name,text=src){
  const needle='function '+name+'(';
  const start=text.indexOf(needle);
  assert(start>=0,'missing layout function '+name);
  assert.equal(text.indexOf(needle,start+needle.length),-1,'duplicate '+name);
  const end=text.indexOf('\nfunction ',start+needle.length);
  assert(end>start,'missing boundary for '+name);
  return text.slice(start,end);
}
const layoutBaseline={
  // Re-pinned 2026-11-17: user-directed sixth main tab (買い目,
  // between 予想 and オッズ) on the race page.
  // Re-pinned 2026-11-17 (v349): user-directed merge of the forecast
  // table into the racecard — five main tabs, the 予想 tab retired,
  // the entry tab labelled 出走表.
  "cinematicTabs": "47b27e9effd6f873",
  "smartRaceTopBar": "6f0925af17890feb",
  // Re-pinned 2026-11-17: user-directed removal of the yellow
  // result-status box (smartInlineResult) from the race header.
  "smartRaceHead": "1ec9637151efc9fd",
  "renderPicker": "8b81f0479683023d",
  // Approved removal of adjacent AI stats globals; favoriteHomeSection body is unchanged.
  "favoriteHomeSection": "d85550a902ac987f",
  // Re-pinned 2026-11-17 (v349): the tabbed horse detail now renders
  // on every forecast lane — the legacyEngineDisabled past-runs-only
  // stub that hid the detail is removed (user report: tapping a
  // horse name did not open the detail).
  "horseDetailPage": "61dbcbbe3684015f",
  // Re-pinned 2026-11-17: user-directed tickets subpage routing and
  // removal of the trailing ticket frame (the plan now lives only on
  // the 買い目 tab, never duplicated under other tabs).
  // Re-pinned 2026-11-17 (v349): the 予想 subpage routing is removed
  // with the merged entry table, and the compact marks frame is no
  // longer appended under the entry panel (the table carries the
  // marks itself).
  "renderRace": "0a51bd471302ad04"
};
const baseSource=baselineRef?baseText('arvexq/ui/static/app.js'):null;
for(const [name,expected] of Object.entries(layoutBaseline))
  assert.equal(fingerprint(functionBody(name)),baselineRef?fingerprint(functionBody(name,baseSource)):expected,'DO_NOT_CHANGE_ARVEXQ_UI_LAYOUT: '+name);
assert.match(src,/function savedRevisionOriginalHtml\(r\)\{[\s\S]*?return '';/);
for(const legacy of ['savedRevisionDiagnosisPanel','savedRevisionHorseDetail','serverFrozenPrediction'])
  assert(!src.includes('function '+legacy+'('),'retired publication function resurrected: '+legacy);
assert(!src.includes('p.savedForecastRevision?'),'retired revision fallback resurrected');
console.log('ARVEXQ_DESIGN_UNCHANGED_AND_LEGACY_VIEWS_REMOVED_PASS');
