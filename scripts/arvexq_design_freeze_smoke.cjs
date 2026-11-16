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
  "arvexq/ui/static/sports/unified-home.css": "10899d661f666180",
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
  "cinematicTabs": "f04fa416e3c7313b",
  "smartRaceTopBar": "6f0925af17890feb",
  "smartRaceHead": "d33922ddb12cd467",
  "renderPicker": "8b81f0479683023d",
  // Approved removal of adjacent AI stats globals; favoriteHomeSection body is unchanged.
  "favoriteHomeSection": "d85550a902ac987f",
  "horseDetailPage": "df827cb40bc07925",
  "renderRace": "36c793cb7ecc4b86"
};
const baseSource=baselineRef?baseText('arvexq/ui/static/app.js'):null;
for(const [name,expected] of Object.entries(layoutBaseline))
  assert.equal(fingerprint(functionBody(name)),baselineRef?fingerprint(functionBody(name,baseSource)):expected,'DO_NOT_CHANGE_ARVEXQ_UI_LAYOUT: '+name);
assert.match(src,/function savedRevisionOriginalHtml\(r\)\{[\s\S]*?return '';/);
for(const legacy of ['savedRevisionDiagnosisPanel','savedRevisionHorseDetail','serverFrozenPrediction'])
  assert(!src.includes('function '+legacy+'('),'retired publication function resurrected: '+legacy);
assert(!src.includes('p.savedForecastRevision?'),'retired revision fallback resurrected');
console.log('ARVEXQ_DESIGN_UNCHANGED_AND_LEGACY_VIEWS_REMOVED_PASS');
