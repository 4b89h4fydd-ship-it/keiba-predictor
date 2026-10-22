// Visual freeze for the approved ARVEXQ layout while removing old calculation logic.
// Intentional layout changes require explicit user approval and an updated baseline.
'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const root=path.resolve(__dirname,'..');
const MASK=(1n<<64n)-1n;
function fingerprint(text){
  let h=14695981039346656037n;
  for(let i=0;i<text.length;i++)h=((h^BigInt(text.charCodeAt(i)))*1099511628211n)&MASK;
  return h.toString(16).padStart(16,'0');
}
const styleBaseline={
  "arvexq/ui/static/styles.css": "924bf5a30829c3bb",
  "arvexq/ui/static/styles/legacy_v118_v221.css": "017f3b66e81a6bea",
  "arvexq/ui/static/styles/race_v222_plus.css": "41af5152406d59ef",
  "arvexq/ui/static/sports/unified-home.css": "41dfa35af79e90bf",
  "arvexq/ui/static/sports/all-races.css": "03c0b3e12ceff2a1",
  "arvexq/ui/static/sports/pull-refresh.css": "498df97b7b5627bb",
  "arvexq/ui/static/research/research_view.css": "702cfda2ceefabd8",
  "arvexq/ui/static/betting/bet_ui.css": "ee96c3e4c06763d4"
};
for(const [name,expected] of Object.entries(styleBaseline)){
  const actual=fingerprint(fs.readFileSync(path.join(root,name),'utf8'));
  assert.equal(actual,expected,'DO_NOT_CHANGE_ARVEXQ_CSS_LAYOUT: '+name);
}
const src=fs.readFileSync(path.join(root,'arvexq/ui/static/app.js'),'utf8');
function functionBody(name){
  const needle='function '+name+'(';
  const start=src.indexOf(needle);
  assert(start>=0,'missing layout function '+name);
  assert.equal(src.indexOf(needle,start+needle.length),-1,'duplicate '+name);
  const end=src.indexOf('\nfunction ',start+needle.length);
  assert(end>start,'missing boundary for '+name);
  return src.slice(start,end);
}
const layoutBaseline={
  "cinematicTabs": "d7aa73a99c251411",
  "smartRaceTopBar": "6f0925af17890feb",
  "smartRaceHead": "d99dff533e6b1bb3",
  "renderPicker": "8b81f0479683023d",
  // Approved removal of adjacent AI stats globals; favoriteHomeSection body is unchanged.
  "favoriteHomeSection": "d85550a902ac987f",
  "horseDetailPage": "acb13e0e1920774a",
  "renderRace": "14e7f4c710086edc"
};
for(const [name,expected] of Object.entries(layoutBaseline))
  assert.equal(fingerprint(functionBody(name)),expected,'DO_NOT_CHANGE_ARVEXQ_UI_LAYOUT: '+name);
assert.match(src,/function savedRevisionOriginalHtml\(r\)\{[\s\S]*?return '';/);
for(const legacy of ['savedRevisionDiagnosisPanel','savedRevisionHorseDetail','serverFrozenPrediction'])
  assert(!src.includes('function '+legacy+'('),'retired publication function resurrected: '+legacy);
assert(!src.includes('p.savedForecastRevision?'),'retired revision fallback resurrected');
console.log('ARVEXQ_DESIGN_UNCHANGED_AND_LEGACY_VIEWS_REMOVED_PASS');
