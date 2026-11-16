// Smoke test for the client-side volatility risk label （堅／普／荒） port
// (arvexq/ui/static/forecast/risk_label.js). The client module must agree
// with the server overlay function (workers/api_risk_label.mjs) on every
// input, including the arvexqFullPayload envelope restore path used for
// thin day details. Pure-function checks only; no network or D1 access.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import zlib from 'node:zlib';
import {createHash} from 'node:crypto';
import {computeRiskLabel as serverCompute, riskLabelGap as serverGap} from '../workers/api_risk_label.mjs';

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
assert.equal(client.version, 'arvexq-risk-label-v1');

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
  // Dominant favourite, small field, deep evidence -> 堅.
  detail({
    probs: [0.62, 0.15, 0.08, 0.05, 0.04, 0.03, 0.02, 0.01],
    abilities: [0.9, 0.4, 0.3, 0.25, 0.2, 0.18, 0.15, 0.1],
    odds: [1.6, 5.0, 9.0, 15.0, 20.0, 30.0, 45.0, 60.0],
    evidence: [8, 8, 8, 7, 8, 6, 8, 5],
  }),
  // Flat probabilities, weak favourite, big field, thin evidence -> 荒.
  detail({
    probs: Array(16).fill(1 / 16),
    abilities: Array(16).fill(0.3),
    odds: Array(16).fill(12.0),
    evidence: Array(16).fill(1),
  }),
  // No unifiedForecast -> no label.
  {circuit: '地方', horses: []},
  // A roster runner without sealed odds -> no label.
  detail({
    probs: [0.5, 0.3, 0.2],
    abilities: [0.8, 0.4, 0.3],
    odds: [2.0, 4.0, null],
    evidence: [8, 8, 8],
  }),
  // Ability coverage below 80% -> no label.
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
for (const d of cases) {
  sameJson(client.computeRiskLabel(d), serverCompute(d));
}
assert.equal(client.computeRiskLabel(cases[0]).label, '堅');
assert.equal(client.computeRiskLabel(cases[1]).label, '荒');
assert.equal(client.computeRiskLabel(cases[5]).segment, 'jra');

// Envelope restore: a thin detail carrying only the sealed envelope must
// produce exactly the label of the full detail it restores to.
{
  const full = cases[0];
  full.id = 'nar-2026-11-16-金沢-05';
  const raw = Buffer.from(JSON.stringify(full), 'utf8');
  const gz = zlib.gzipSync(raw);
  const thin = {
    id: full.id,
    circuit: '地方',
    arvexqFullPayload: {
      version: 'arvexq-full-payload-v1',
      bytes: raw.length,
      sha256: createHash('sha256').update(raw).digest('hex'),
      gzipBase64: gz.toString('base64'),
    },
  };
  assert.equal(client.computeRiskLabel(thin), null);
  const label = await client.ensureRiskLabel(thin);
  sameJson(label, serverCompute(full));
  sameJson(thin.riskLabel, label);
  // A tampered envelope restores nothing and labels nothing.
  const bad = JSON.parse(JSON.stringify(thin));
  bad.riskLabel = undefined;
  bad.arvexqFullPayload.sha256 = '0'.repeat(64);
  assert.equal(await client.ensureRiskLabel(bad), null);
  assert.equal(bad.riskLabel, undefined);
}

// Win odds of exactly 1.0 are genuine in the NAR feed (official results
// record them): the favourite at 1.0 must still get a label, identically
// on client and server.
{
  const d = detail({
    probs: [0.78, 0.08, 0.05, 0.04, 0.03, 0.02],
    abilities: [0.95, 0.4, 0.3, 0.25, 0.2, 0.15],
    odds: [1.0, 12.0, 20.0, 28.0, 40.0, 60.0],
    evidence: [9, 8, 8, 7, 8, 6],
  });
  const lbl = client.computeRiskLabel(d);
  assert.ok(lbl, 'odds 1.0 favourite still labelled');
  sameJson(lbl, serverCompute(d));
  assert.equal(client.riskLabelGap(d), null);
  assert.equal(serverGap(d), null);
  // Odds below 1 remain invalid.
  const bad = detail({
    probs: [0.5, 0.3, 0.2],
    abilities: [0.8, 0.4, 0.3],
    odds: [0.5, 4.0, 6.0],
    evidence: [8, 8, 8],
  });
  assert.equal(client.computeRiskLabel(bad), null);
  sameJson(client.computeRiskLabel(bad), serverCompute(bad));
}

// Gap diagnosis: no label, but a forecast exists -> the reason is named,
// identically on client and server. No forecast -> no gap (silence is
// correct there: the race is simply unforecast).
{
  const abilityGap = detail({
    probs: [0.4, 0.25, 0.15, 0.1, 0.1],
    abilities: [0.8, 0.4, null, null, 0.2],
    odds: [2.5, 4.0, 7.0, 11.0, 11.0],
    evidence: [8, 8, 8, 8, 8],
  });
  assert.equal(client.computeRiskLabel(abilityGap), null);
  sameJson(client.riskLabelGap(abilityGap), serverGap(abilityGap));
  assert.equal(client.riskLabelGap(abilityGap).code, 'ability-coverage');
  assert.equal(client.riskLabelGap(abilityGap).abilityCovered, 3);

  const scratched = detail({
    probs: [0.4, 0.3, 0.2, 0.1],
    abilities: [0.8, 0.5, 0.4, 0.3],
    odds: [2.0, 4.0, 6.0, null],
    evidence: [8, 8, 8, 8],
  });
  scratched.horses[3].scratched = true;
  scratched.horses[3].status = '出走取消';
  assert.equal(client.riskLabelGap(scratched).code, 'market-odds-scratched');
  sameJson(client.riskLabelGap(scratched), serverGap(scratched));

  const missingOdds = detail({
    probs: [0.4, 0.3, 0.2, 0.1],
    abilities: [0.8, 0.5, 0.4, 0.3],
    odds: [2.0, 4.0, 6.0, null],
    evidence: [8, 8, 8, 8],
  });
  assert.equal(client.riskLabelGap(missingOdds).code, 'market-odds-missing');
  sameJson(client.riskLabelGap(missingOdds), serverGap(missingOdds));

  const noEvidence = detail({
    probs: [0.4, 0.3, 0.2, 0.1],
    abilities: [0.8, 0.5, 0.4, 0.3],
    odds: [2.0, 4.0, 6.0, 9.0],
    evidence: [8, 8, 8, 8],
  });
  delete noEvidence.masterAnalysis;
  assert.equal(client.riskLabelGap(noEvidence).code, 'evidence-missing');
  sameJson(client.riskLabelGap(noEvidence), serverGap(noEvidence));

  assert.equal(client.riskLabelGap({circuit: '地方', horses: []}), null);
  assert.equal(serverGap({circuit: '地方', horses: []}), null);
  assert.equal(client.riskLabelGap(cases[0]), null);
  assert.equal(serverGap(cases[0]), null);
}

// Envelope restore for the gap: a thin detail whose full payload has an
// ability-coverage gap resolves the gap and stashes it on the detail.
{
  const full = detail({
    probs: [0.4, 0.25, 0.15, 0.1, 0.1],
    abilities: [0.8, 0.4, null, null, 0.2],
    odds: [2.5, 4.0, 7.0, 11.0, 11.0],
    evidence: [8, 8, 8, 8, 8],
  });
  full.id = 'nar-2026-11-16-大井-12';
  const raw = Buffer.from(JSON.stringify(full), 'utf8');
  const gz = zlib.gzipSync(raw);
  const thin = {
    id: full.id,
    circuit: '地方',
    arvexqFullPayload: {
      version: 'arvexq-full-payload-v1',
      bytes: raw.length,
      sha256: createHash('sha256').update(raw).digest('hex'),
      gzipBase64: gz.toString('base64'),
    },
  };
  assert.equal(client.riskLabelGap(thin), null);
  const gap = await client.ensureRiskLabelGap(thin);
  assert.equal(gap.code, 'ability-coverage');
  sameJson(thin.riskLabelGap, gap);
  // A labelled race resolves no gap even through the envelope path.
  const labelled = JSON.parse(JSON.stringify(thin));
  labelled.riskLabel = client.computeRiskLabel(cases[0]);
  assert.equal(await client.ensureRiskLabelGap(labelled), null);
}

console.log('RISK_LABEL_CLIENT_SMOKE_PASS');
