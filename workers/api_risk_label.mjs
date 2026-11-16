// Volatility risk label （堅／普／荒） computed at API read time from the stored
// full detail payload. Display-only: stored payloads are never rewritten.
//
// Method (validated 2026-11-16, volatility-risk-20261116): five pre-race
// components, each mapped through a fixed per-segment ECDF table
// (api_risk_label_constants.mjs, built from the validation corpus), averaged
// into a risk score in [0,1]. Bands are the validation's pre-fixed absolute
// bands: score < 1/3 -> 堅， < 2/3 -> 普， otherwise 荒.
//   ent_model          normalized entropy of the forecast win probabilities
//   weak_fav_mkt       1 - max normalized market implied probability
//   field              number of runners on the forecast roster
//   thin_share         share of runners with evidenceRuns <= 2
//   weak_ability_conc  1 - max(abilityScore) / sum(abilityScore)
// A race gets NO label when any component cannot be computed from stored
// material (no unifiedForecast, missing odds/evidence/ability coverage):
// missing material is reported as absence, never estimated.
import {RISK_ECDF_TABLES} from './api_risk_label_constants.mjs';

export const RISK_LABEL_VERSION = 'arvexq-risk-label-v1';

function ecdf(table, value) {
  const bp = table.bp;
  let lo = 0, hi = bp.length;
  while (lo < hi) {
    const mid = (lo + hi) >> 1;
    if (bp[mid] < value) lo = mid + 1; else hi = mid;
  }
  // lo = number of grid breakpoints strictly below value (grid = p1..p99).
  const p = (lo + 0.5) / 100;
  return Math.min(0.995, Math.max(0.005, p));
}

function finite(x) {
  if (x === null || x === undefined || x === '') return null;
  const v = Number(x);
  return Number.isFinite(v) ? v : null;
}

// detail: a full (restored) race detail payload. Both API surfaces serve
// this same stored detail (the day list carries it inside the
// arvexqFullPayload envelope; the race endpoint restores that envelope), so
// a label computed from it is identical on the tiles and the detail header.
// The market component uses the win odds sealed inside the detail at
// forecast capture time — the same kind of pre-race market snapshot the
// validation used — not live odds, so the label stays fixed with the
// forecast. Returns {version, label, score, segment} or null.
export function computeRiskLabel(detail) {
  if (!detail || typeof detail !== 'object') return null;
  const uf = detail.unifiedForecast;
  if (!uf || !Array.isArray(uf.roster) || !Array.isArray(uf.diagnosis)) return null;
  const roster = uf.roster
    .map((x) => Number(x && x.horseNumber))
    .filter((n) => Number.isInteger(n) && n > 0);
  if (roster.length < 3 || new Set(roster).size !== roster.length) return null;
  const segment = detail.circuit === '地方' || uf.circuit === '地方' ? 'nar'
    : detail.circuit === '中央' || uf.circuit === '中央' ? 'jra' : null;
  if (!segment) return null;
  const table = RISK_ECDF_TABLES[segment];
  if (!table) return null;

  const diag = new Map();
  for (const d of uf.diagnosis) {
    const n = Number(d && d.horseNumber);
    if (Number.isInteger(n) && n > 0 && !diag.has(n)) diag.set(n, d);
  }

  // ent_model: forecast win probabilities for every roster runner.
  let probSum = 0;
  const probs = [];
  for (const n of roster) {
    const p = finite(diag.get(n)?.winProbability);
    if (p === null || p < 0) return null;
    probs.push(p);
    probSum += p;
  }
  if (!(probSum > 0)) return null;
  let ent = 0;
  for (const p of probs) {
    const q = p / probSum;
    if (q > 0) ent -= q * Math.log(q);
  }
  ent /= Math.log(roster.length);

  // weak_fav_mkt: win odds sealed in the detail's horses, normalized
  // within the race (the corpus implied_prob sums to 1 the same way).
  const horseByNo = new Map();
  for (const h of detail.horses || []) {
    const n = Number(h && h.horseNumber);
    if (Number.isInteger(n) && n > 0 && !horseByNo.has(n)) horseByNo.set(n, h);
  }
  let rawSum = 0, rawMax = 0;
  for (const n of roster) {
    const odds = finite(horseByNo.get(n)?.winOdds);
    if (odds === null || odds <= 1) return null;
    const raw = 1 / odds;
    rawSum += raw;
    if (raw > rawMax) rawMax = raw;
  }
  if (!(rawSum > 0)) return null;
  const weakFav = 1 - rawMax / rawSum;

  // thin_share: evidence runs recorded by the issuing analysis.
  const runners = detail.masterAnalysis && Array.isArray(detail.masterAnalysis.runners)
    ? detail.masterAnalysis.runners : null;
  if (!runners) return null;
  const evByNo = new Map();
  for (const r of runners) {
    const n = Number(r && r.horseNumber);
    if (Number.isInteger(n) && n > 0 && !evByNo.has(n)) evByNo.set(n, finite(r.evidenceRuns));
  }
  let thin = 0;
  for (const n of roster) {
    const ev = evByNo.get(n);
    if (ev === null || ev === undefined) return null;
    if (ev <= 2) thin += 1;
  }
  const thinShare = thin / roster.length;

  // weak_ability_conc: diagnosis ability scores, >=80% coverage required
  // (same rule as the validation; below that the component is missing).
  let abCount = 0, abSum = 0, abMax = 0;
  for (const n of roster) {
    const a = finite(diag.get(n)?.abilityScore);
    if (a !== null) {
      abCount += 1;
      abSum += a;
      if (a > abMax) abMax = a;
    }
  }
  if (abCount < 0.8 * roster.length || !(abSum > 0)) return null;
  const weakAb = 1 - abMax / abSum;

  const components = {
    ent_model: ent,
    weak_fav_mkt: weakFav,
    field: roster.length,
    thin_share: thinShare,
    weak_ability_conc: weakAb,
  };
  const keys = ['ent', 'weak_fav', 'field', 'thin_share', 'weak_ab'];
  const values = [ent, weakFav, roster.length, thinShare, weakAb];
  let score = 0;
  for (let i = 0; i < keys.length; i++) score += ecdf(table[keys[i]], values[i]);
  score /= keys.length;
  const label = score < 1 / 3 ? '堅' : score < 2 / 3 ? '普' : '荒';
  return {
    version: RISK_LABEL_VERSION,
    label,
    score: Math.round(score * 1000) / 1000,
    segment,
    components: Object.fromEntries(
      Object.entries(components).map(([k, v]) => [k, Math.round(v * 10000) / 10000])),
  };
}
