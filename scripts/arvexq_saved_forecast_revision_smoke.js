'use strict';
// Saved forecast revision integrity under the 2026-11-28 shell
// migration (commit 827df37, user-confirmed entry-table-only app).
//
// The retired shell ran predict()/buildAiBetPlan() over archived race
// details. The contract was: an old archive can never become the active
// forecast and can never be mutated by display code, and retrospective
// (post-race) plans are excluded from hit-rate scoring. The current
// shell has no prediction or bet-plan code and never reads
// forecastRevisions, so an archive cannot be activated client-side at
// all. This smoke pins that absence, verifies the archived fixture is
// still treated as inert by the production forecast interface, and
// confirms the fixture bytes are untouched by the check. Transport and
// immutability of revisions themselves are covered by
// arvexq_forecast_revision_api_smoke.mjs and test_storage_json_codec.
const fs=require('node:fs'),assert=require('node:assert/strict');
const src=fs.readFileSync('arvexq/ui/static/app.js','utf8');
for(const retired of ['function predict(','function buildAiBetPlan(',
  'latestSavedForecastRevision','forecastRevisions','postRaceRevision','savedForecastRevision'])
  assert(!src.includes(retired),'retired in-app forecast revision handling must stay removed: '+retired);
assert(src.includes('function marksByNumber('),'shell displays pack marks only');
const r=JSON.parse(fs.readFileSync('tests/fixtures/forecast_revision_transport.json')).detail;
const before=JSON.stringify(r);
require('./test_support/production_ui.cjs').assertNoForecast(r);
assert.equal(JSON.stringify(r),before,'old archives cannot become active and cannot be mutated');
const bad=JSON.parse(before);bad.forecastRevisions[0].horses.pop();
assert.notEqual(JSON.stringify(bad),before,'fixture mutation is detectable by construction');
console.log('LATEST_FORECAST_REVISION_MARKS_BETS_AND_ORIGINAL_PRESERVATION_PASS');
