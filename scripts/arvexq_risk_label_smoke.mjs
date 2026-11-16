// Smoke test for the volatility risk label （堅／普／荒）.
// Pure-function checks only; no network or D1 access.
import assert from 'node:assert/strict';
import {computeRiskLabel} from '../workers/api_risk_label.mjs';
import {overlayRaceResponse, overlayDayResponse} from '../workers/api_display_overlay.mjs';

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

// 1) Dominant favourite, small field, deep evidence -> 堅.
{
  const d = detail({
    probs: [0.62, 0.15, 0.08, 0.05, 0.04, 0.03, 0.02, 0.01],
    abilities: [0.9, 0.4, 0.3, 0.25, 0.2, 0.18, 0.15, 0.1],
    odds: [1.6, 5.0, 9.0, 15.0, 20.0, 30.0, 45.0, 60.0],
    evidence: [8, 8, 8, 7, 8, 6, 8, 5],
  });
  const label = computeRiskLabel(d);
  assert.equal(label.label, '堅');
  assert.equal(label.segment, 'nar');
  assert.ok(label.score < 1 / 3);
}

// 2) Flat probabilities, weak favourite, big field, thin evidence -> 荒.
{
  const n = 16;
  const d = detail({
    probs: Array(n).fill(1 / n),
    abilities: Array(n).fill(0.3),
    odds: Array(n).fill(12.0),
    evidence: Array(n).fill(1),
  });
  const label = computeRiskLabel(d);
  assert.equal(label.label, '荒');
  assert.ok(label.score >= 2 / 3);
}

// 3) Missing unifiedForecast -> no label (never fabricated).
{
  assert.equal(computeRiskLabel({circuit: '地方', horses: []}), null);
}

// 4) Any roster runner without sealed odds -> no label.
{
  const d = detail({
    probs: [0.5, 0.3, 0.2],
    abilities: [0.8, 0.4, 0.3],
    odds: [2.0, 4.0, null],
    evidence: [8, 8, 8],
  });
  assert.equal(computeRiskLabel(d), null);
}

// 5) Ability coverage below 80% -> no label (validation's missing rule).
{
  const d = detail({
    probs: [0.4, 0.25, 0.15, 0.1, 0.1],
    abilities: [0.8, 0.4, null, null, 0.2],
    odds: [2.5, 4.0, 7.0, 11.0, 11.0],
    evidence: [8, 8, 8, 8, 8],
  });
  assert.equal(computeRiskLabel(d), null);
}

// 6) Race response: label lands on detail AND summary, identically.
{
  const d = detail({
    probs: [0.62, 0.15, 0.08, 0.05, 0.04, 0.03, 0.02, 0.01],
    abilities: [0.9, 0.4, 0.3, 0.25, 0.2, 0.18, 0.15, 0.1],
    odds: [1.6, 5.0, 9.0, 15.0, 20.0, 30.0, 45.0, 60.0],
    evidence: [8, 8, 8, 7, 8, 6, 8, 5],
  });
  d.id = 'nar-2026-11-16-金沢-05';
  const body = {ok: true, race_id: d.id, summary: {weather: '晴', condition: '良'}, detail: d, odds: []};
  const res = new Response(JSON.stringify(body), {headers: {'content-type': 'application/json'}});
  const patched = await (await overlayRaceResponse(res)).json();
  assert.equal(patched.detail.riskLabel.label, '堅');
  assert.deepEqual(patched.summary.riskLabel, patched.detail.riskLabel);
}

// 7) Day response: thin detail without forecast material stays unlabelled,
//    and a labelled detail mirrors the same object onto its summary.
{
  const d = detail({
    probs: [0.62, 0.15, 0.08, 0.05, 0.04, 0.03, 0.02, 0.01],
    abilities: [0.9, 0.4, 0.3, 0.25, 0.2, 0.18, 0.15, 0.1],
    odds: [1.6, 5.0, 9.0, 15.0, 20.0, 30.0, 45.0, 60.0],
    evidence: [8, 8, 8, 7, 8, 6, 8, 5],
  });
  d.id = 'r-solid';
  const body = {
    ok: true, date: '2026-11-16',
    races: [{id: 'r-solid', weather: '晴', condition: '良'}, {id: 'r-thin', weather: '晴', condition: '良'}],
    details: [d, {id: 'r-thin', weather: '不明', condition: '不明'}],
  };
  const env = {DB: {prepare() { return {bind() { return {all: async () => ({results: []})}; }}; }}};
  const res = new Response(JSON.stringify(body), {headers: {'content-type': 'application/json'}});
  const patched = await (await overlayDayResponse(res, env, new URL('https://example.invalid/api/day?date=2026-11-16'))).json();
  assert.equal(patched.details[0].riskLabel.label, '堅');
  assert.deepEqual(patched.races[0].riskLabel, patched.details[0].riskLabel);
  assert.equal(patched.details[1].riskLabel, undefined);
  assert.equal(patched.races[1].riskLabel, undefined);
}

console.log('RISK_LABEL_SMOKE_PASS');
