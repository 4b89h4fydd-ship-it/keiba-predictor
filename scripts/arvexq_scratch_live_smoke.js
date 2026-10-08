const assert = require('node:assert/strict');
const fs = require('node:fs');
const source = fs.readFileSync('arvexq/ui/static/app.js', 'utf8');

function extract(start, end) {
  const a = source.indexOf('function ' + start + '(');
  const b = source.indexOf('\nfunction ' + end + '(', a);
  assert.ok(a >= 0 && b > a, 'could not isolate ' + start);
  return source.slice(a, b);
}
const n = (v, fallback = 0) => {
  const x = Number(v);
  return v == null || !Number.isFinite(x) ? fallback : x;
};
const state = {
  race: {id: 'nar-2026-10-08-園田-05',
    _prediction: {old: true},
    horses: [
      {horseNumber: 4, name: 'ミルトコルサ', winOdds: 5.4, popularity: 3},
      {horseNumber: 5, name: '稼働馬', winOdds: 3.2, popularity: 2}
    ]},
  pred: {stale: true}, analysisSaved: {stale: true}
};
const impl = [
  extract('isScratchHorse', 'analysisRace'),
  extract('reflectUseful', 'raceDisplayCoreReady'),
  extract('mergeOddsPayload', 'refreshRaceAfterCollect')
].join('\n');
const obj = new Function('state', 'n', impl +
  '\nreturn {isScratchHorse,edgeOddsRow,mergeHorseReflection,mergeOddsPayload};')(state, n);
const {isScratchHorse, edgeOddsRow, mergeHorseReflection, mergeOddsPayload} = obj;
const official = edgeOddsRow({
  race_id: state.race.id,
  horse_no: 4, horse_status: '出走取消',
  win_odds: null, popularity: null
});
assert.equal(official.scratched, true);
assert.equal(official.horseNumber, 4);
assert.equal(official.status, '出走取消');
assert.equal(mergeOddsPayload({horses: [official]}), true);
assert.equal(state.race.horses[0].scratched, true);
assert.equal(state.race.horses[0].status, '出走取消');
assert.equal(state.race.horses[0].winOdds, null);
assert.equal(state.race.horses[1].winOdds, 3.2);
assert.equal(state.race._prediction, undefined, 'prediction inputs invalidated');
assert.equal(state.pred, null, 'stale predicted runner must be removed');
assert.equal(isScratchHorse(state.race.horses[0]), true);

// A later stale market reply cannot re-enable the scratched horse.
assert.equal(mergeOddsPayload({horses: [
  {horseNumber: 4, status: '通常', scratched: false, winOdds: 8.4}
]}), false);
assert.equal(state.race.horses[0].status, '出走取消');
assert.equal(state.race.horses[0].winOdds, null);
const preserved = mergeHorseReflection(
  state.race.horses[0],
  {horseNumber: 4, status: '通常', scratched: false},
  {horseNumber: 4, status: '通常', scratched: false}
);
assert.equal(preserved.status, '出走取消');
assert.equal(preserved.scratched, true);
assert.match(source, /scratch\?' disabled aria-disabled="true"'/);
assert.match(source, /scratch\?' scratched'/);
assert.match(source, /if\(isScratchHorse\(h\)\)return '<span class="odd scratch-odds">取消/);
console.log('ARVEXQ_SCRATCH_LIVE_REFLECTION_OK');
