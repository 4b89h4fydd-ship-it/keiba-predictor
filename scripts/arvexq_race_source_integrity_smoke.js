/* Race display source integrity under the 2026-11-28 shell migration
   (commit 827df37, user-confirmed entry-table-only app).
 *
 * The retired shell opened a race through openRace(): one D1 display
 * fetch, a verified static card first, and the compact racecard only on
 * roster failure. That whole open path was removed with the rich UI.
 * The current shell has exactly one source: the static packs
 * (api-static/day/<date>.json and api-static/race/<raceId>.json). This
 * smoke now pins that single-source contract:
 *   - no D1/edge fetch, no saved-snapshot restore, no device race cache
 *     exists in the shell, so no legacy path can overwrite pack facts;
 *   - marks and probabilities render only from the pack's
 *     unifiedForecast, keyed by horse number;
 *   - Banei exclusion can no longer be resurrected by a device cache or
 *     a legacy list merge, because neither exists in the shell (the
 *     exclusion itself is enforced when packs are built, server-side).
 * The read-only race-open repair workflow, the deprecated observed
 * model adapter, and the physical deletion of the retired scorers are
 * unchanged parts of the original contract and are kept as-is. */
const assert=require('node:assert/strict');
const fs=require('node:fs');
const src=fs.readFileSync('arvexq/ui/static/app.js','utf8');
// Single source: static packs only.
assert(src.includes("arvexqBasePath() + 'api-static/day/'"),'day pack is the venue/race source');
assert(src.includes("arvexqBasePath() + 'api-static/race/'"),'race pack is the race source');
assert(src.includes('function staticDayUrl(')&&src.includes('function staticRaceUrl('),
  'pack URL builders are the only race data entry points');
for(const retired of ['function openRace(','fetchEdgeRace(','fetchRacecardOnly(',
  'hydrateStaticRacecardFirst(','window.ARVEXQSavedSnapshot','saved-snapshot-restored',
  'function loadRaceCache(','function saveRaceCache(','function mergeBootstrap(',
  'function homePickAlert(','function smartHomeHub(','function specialForecastRaceCandidates(',
  'evictRetiredRaceCaches();'])
  assert(!src.includes(retired),'retired race-open path must stay removed: '+retired);
// Display authority: pack unifiedForecast, by horse number, nothing computed.
assert(src.includes('function marksByNumber('),'marks come from the pack by horse number');
assert(src.includes('function probabilitiesByNumber('),'probabilities come from the pack by horse number');
assert(src.includes('uf.diagnosis')&&src.includes('uf.marks'),
  'shell reads unifiedForecast diagnosis and marks only');
for(const retired of ['function predict(','function assignPredictionMarks(',
  'function racecardEntryRow(','function homePickCounts(','function renderHome(){'])
  assert(!src.includes(retired),'retired in-app computation must stay removed: '+retired);
// Banei resurrection vectors (device cache restore, legacy list merge,
// direct-route bypass of the filter) are gone with the caches themselves.
for(const retired of ['function isExcludedBanei(','function activeVenueRaces('])
  assert(!src.includes(retired),'shell has no list of its own to filter: '+retired);
assert(!src.includes('localStorage'),'shell keeps no device race cache at all');
const workflow=fs.readFileSync('.github/workflows/arvexq-race-open-repair.yml','utf8');
assert(workflow.includes('contents: read'));
assert(!workflow.includes('git push')&&!workflow.includes('Apply repair'));
assert(!fs.existsSync('scripts/arvexq_patch_race_open_reliability.py'));
const model=fs.readFileSync('arvexq/prediction/observed_model.py','utf8');
assert(model.includes('clear_marks(detail)'), 'retired adapter clears old fields');
assert(!model.includes('sum(observations)'), 'old scoring implementation removed');
assert(!fs.existsSync('arvexq/prediction/factor_model.py'),'retired central three-factor scorer must be physically deleted');
assert(!fs.existsSync('arvexq/prediction/nar_model.py'),'duplicate local scorer must be physically deleted');
assert(!fs.existsSync('arvexq/prediction/honmei_gate.py'),'retired parallel axis scorer must be deleted');
console.log('ARVEXQ_SINGLE_SOURCE_STATIC_PACK_RACE_DISPLAY_OK');
console.log('APP_BANEI_EXCLUSION_PACK_SIDE_NO_CLIENT_RESURRECTION_PASS');
