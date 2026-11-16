// Smoke test for the upset forecast （荒れ予想） derivation
// (arvexq/ui/static/forecast/risk_label.js upsetFromRisk/computeUpsetForecast).
// The upset forecast is a presentation of the validated volatility risk
// score: its level bands are the label's own pre-fixed bands, so level and
// label must always agree （堅=低 / 普=中 / 荒=高）. The client module must
// agree with the server reference (workers/api_risk_label.mjs) on every
// input. Pure-function checks only; no network or D1 access.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import {
  computeRiskLabel as serverCompute,
  computeUpsetForecast as serverUpset,
  upsetFromRisk as serverUpsetFromRisk,
} from '../workers/api_risk_label.mjs';

const src = fs.readFileSync(new URL('../arvexq/ui/static/forecast/risk_label.js', import.meta.url), 'utf8');
const sandbox = {};
sandbox.window = sandbox;
for (const k of ['atob', 'Blob', 'DecompressionStream', 'Response', 'crypto', 'TextDecoder']) {
  sandbox[k] = globalThis[k];
}
vm.createContext(sandbox);
vm.runInContext(src, sandbox);
const client = sandbox.ARVEXQRiskLabel;
assert.ok(client, 'ARVEXQRiskLabel exposed');
assert.equal(client.upsetVersion, 'arvexq-upset-forecast-v1');
assert.equal(typeof client.computeUpsetForecast, 'function');
assert.equal(typeof client.upsetFromRisk, 'function');

function detail({probs, abilities, odds, evidence, circuit = '地方'}) {
  const roster = probs.map((_, i) => ({horseNumber: i + 1, name: 'H' + (i + 1)}));
  return {
    circuit,
    horses: odds.map((o, i) => ({horseNumber: i + 1, winOdds: o})),
    unifiedForecast: {
      circuit,
      roster,
      diagnosis: probs.map((p, i) => ({
        horseNumber: i + 1, winProbability: p, abilityScore: abilities[i],
      })),
    },
    masterAnalysis: {runners: evidence.map((e, i) => ({horseNumber: i + 1, evidenceRuns: e}))},
  };
}

const cases = [
  // Dominant favourite, small field, deep evidence -> 堅 / 低.
  detail({
    probs: [0.62, 0.15, 0.08, 0.05, 0.04, 0.03, 0.02, 0.01],
    abilities: [0.9, 0.4, 0.3, 0.25, 0.2, 0.18, 0.15, 0.1],
    odds: [1.6, 5.0, 9.0, 15.0, 20.0, 30.0, 45.0, 60.0],
    evidence: [8, 8, 8, 7, 8, 6, 8, 5],
  }),
  // Flat probabilities, weak favourite, big field, thin evidence -> 荒 / 高.
  detail({
    probs: Array(16).fill(1 / 16),
    abilities: Array(16).fill(0.3),
    odds: Array(16).fill(12.0),
    evidence: Array(16).fill(1),
  }),
  // No unifiedForecast -> no forecast.
  {circuit: '地方', horses: []},
  // A roster runner without sealed odds -> no forecast.
  detail({
    probs: [0.5, 0.3, 0.2],
    abilities: [0.8, 0.4, 0.3],
    odds: [2.0, 4.0, null],
    evidence: [8, 8, 8],
  }),
  // Ability coverage below 80% -> no forecast.
  detail({
    probs: [0.4, 0.25, 0.15, 0.1, 0.1],
    abilities: [0.8, 0.4, null, null, 0.2],
    odds: [2.5, 4.0, 7.0, 11.0, 11.0],
    evidence: [8, 8, 8, 8, 8],
  }),
  // JRA segment table.
  detail({
    probs: [0.3, 0.2, 0.15, 0.1, 0.08, 0.06, 0.05, 0.03, 0.02, 0.01],
    abilities: [0.85, 0.6, 0.5, 0.45, 0.4, 0.35, 0.3, 0.25, 0.2, 0.15],
    odds: [3.0, 5.0, 7.0, 10.0, 14.0, 20.0, 28.0, 40.0, 60.0, 90.0],
    evidence: [10, 9, 8, 8, 7, 6, 5, 5, 4, 3],
    circuit: '中央',
  }),
];

// Objects returned by the client live in the vm realm, so compare by JSON.
function sameJson(a, b) {
  assert.equal(JSON.stringify(a), JSON.stringify(b));
}
const LEVEL_OF_LABEL = {'堅': '低', '普': '中', '荒': '高'};
for (const d of cases) {
  sameJson(client.computeUpsetForecast(d), serverUpset(d));
  const risk = serverCompute(d);
  sameJson(client.upsetFromRisk(client.computeRiskLabel(d)), serverUpsetFromRisk(risk));
  const up = serverUpset(d);
  if (risk === null) {
    assert.equal(up, null);
  } else {
    // The forecast must never contradict the label, and score100 is the
    // label score on a 0-100 scale.
    assert.equal(up.label, risk.label);
    assert.equal(up.level, LEVEL_OF_LABEL[risk.label]);
    assert.equal(up.score100, Math.round(risk.score * 100));
    assert.ok(up.reasons.length >= 1 && up.reasons.length <= 2);
  }
}
assert.equal(client.computeUpsetForecast(cases[0]).level, '低');
assert.equal(client.computeUpsetForecast(cases[1]).level, '高');
assert.equal(client.computeUpsetForecast(cases[5]).segment, 'jra');
assert.equal(client.upsetFromRisk(null), null);
assert.equal(client.upsetFromRisk({label: '堅', score: 0.2, segment: 'nar'}), null);

// Randomised sweep: level/label consistency and client/server agreement
// hold for arbitrary fields, not just the fixed cases.
let seed = 20261116;
function rnd() {
  seed = (seed * 1103515245 + 12345) % 2147483648;
  return seed / 2147483648;
}
for (let t = 0; t < 300; t++) {
  const n = 5 + Math.floor(rnd() * 13);
  const raw = Array.from({length: n}, () => 0.02 + rnd());
  const sum = raw.reduce((a, b) => a + b, 0);
  const d = detail({
    probs: raw.map((x) => x / sum),
    abilities: Array.from({length: n}, () => 0.1 + rnd() * 0.8),
    odds: Array.from({length: n}, () => 1.3 + rnd() * 60),
    evidence: Array.from({length: n}, () => Math.floor(rnd() * 10)),
    circuit: t % 2 ? '中央' : '地方',
  });
  sameJson(client.computeUpsetForecast(d), serverUpset(d));
  const up = serverUpset(d);
  if (up) assert.equal(up.level, LEVEL_OF_LABEL[up.label]);
}

console.log('UPSET_FORECAST_SMOKE_PASS');
