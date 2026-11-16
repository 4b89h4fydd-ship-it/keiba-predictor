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
export const UPSET_FORECAST_VERSION = 'arvexq-upset-forecast-v1';

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
    // Win odds of exactly 1.0 are genuine in the NAR feed (verified in
    // official results: a runner in a small pool can be returned at 1.0,
    // e.g. 金沢 2026-11-16 4R winner, 1番人気, winOdds 1.0 pre-race and in
    // the result). The implied probability 1/1.0 is present, not missing —
    // the validation only excluded races whose implied_prob was missing —
    // so only odds below 1 (or absent / non-finite) make the component
    // uncomputable.
    if (odds === null || odds < 1) return null;
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

export const RISK_LABEL_GAP_VERSION = 'arvexq-risk-label-gap-v1';

// Why a forecast-bearing race has NO label: a display diagnostic, never an
// estimate. Returns null when the race has no issued forecast to judge
// (no unifiedForecast / roster / segment — those races are simply
// unforecast) and null when a label IS computable. Otherwise returns
// {version, code, reason, segment, ...} naming the first component, in
// computeRiskLabel's own check order, that cannot be computed from the
// stored material. The validated population excluded exactly these races
// (implied_prob missing, ability component missing), so for them "no
// label, with the reason shown" is the faithful output.
export function riskLabelGap(detail) {
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
  if (computeRiskLabel(detail)) return null;

  const diag = new Map();
  for (const d of uf.diagnosis) {
    const n = Number(d && d.horseNumber);
    if (Number.isInteger(n) && n > 0 && !diag.has(n)) diag.set(n, d);
  }
  const gap = (code, reason, extra) => Object.assign(
    {version: RISK_LABEL_GAP_VERSION, code, reason, segment}, extra || {});

  // ent_model: every roster runner needs a usable forecast probability.
  for (const n of roster) {
    const p = finite(diag.get(n)?.winProbability);
    if (p === null || p < 0) {
      return gap('forecast-probabilities', '予想確率が不足しているため');
    }
  }

  // weak_fav_mkt: every roster runner needs sealed win odds (>= 1; odds of
  // exactly 1.0 are genuine, see computeRiskLabel). A runner scratched
  // after issuance loses its sealed odds in the stored detail, which is
  // reported as its own reason.
  const horseByNo = new Map();
  for (const h of detail.horses || []) {
    const n = Number(h && h.horseNumber);
    if (Number.isInteger(n) && n > 0 && !horseByNo.has(n)) horseByNo.set(n, h);
  }
  const badOdds = [];
  for (const n of roster) {
    const odds = finite(horseByNo.get(n)?.winOdds);
    if (odds === null || odds < 1) badOdds.push(n);
  }
  if (badOdds.length) {
    const scratched = badOdds.some((n) => {
      const h = horseByNo.get(n);
      return !!h && (h.scratched === true
        || String(h.status || '').includes('出走取消')
        || String(h.status || '').includes('取消'));
    });
    return scratched
      ? gap('market-odds-scratched', '出走取消の馬のオッズがないため', {horses: badOdds})
      : gap('market-odds-missing', 'オッズ情報が不足しているため', {horses: badOdds});
  }

  // thin_share: evidence runs recorded by the issuing analysis.
  const runners = detail.masterAnalysis && Array.isArray(detail.masterAnalysis.runners)
    ? detail.masterAnalysis.runners : null;
  if (!runners) return gap('evidence-missing', '過去走のデータが不足しているため');
  const evByNo = new Map();
  for (const r of runners) {
    const n = Number(r && r.horseNumber);
    if (Number.isInteger(n) && n > 0 && !evByNo.has(n)) evByNo.set(n, finite(r.evidenceRuns));
  }
  for (const n of roster) {
    const ev = evByNo.get(n);
    if (ev === null || ev === undefined) {
      return gap('evidence-missing', '過去走のデータが不足しているため');
    }
  }

  // weak_ability_conc: the issuing engine itself records no ability score
  // for evidence-thin runners （能力スコアなし); below 80% coverage the
  // component is missing by the validation's rule.
  let abCount = 0;
  for (const n of roster) {
    if (finite(diag.get(n)?.abilityScore) !== null) abCount += 1;
  }
  if (abCount < 0.8 * roster.length) {
    return gap('ability-coverage', '能力スコアのない馬が含まれるため',
      {abilityCovered: abCount, field: roster.length});
  }

  return gap('unknown', '判定材料が不足しているため');
}

// ---------------------------------------------------------------------------
// Upset forecast （荒れ予想）: a presentation of the SAME validated risk
// score — no new definition, no new thresholds. The level bands are the
// validation's pre-fixed absolute bands, identical to the label bands, so
// the forecast can never contradict the 堅/普/荒 label:
//   score < 1/3  -> label 堅 / upset level 低
//   score < 2/3  -> label 普 / upset level 中
//   otherwise    -> label 荒 / upset level 高
// score100 is the risk score on a 0-100 scale (SPEC §5.2 波乱リスク帯）.
// reasons is a one-line summary naming the components that contribute most
// to the score (each component's ECDF within the segment, recomputed from
// the label's stored raw component values). For a low-upset race the
// summary names the strongest stabilising components instead.
// NOTE: the score is validated for NAR （地方， 951R) only; for JRA the same
// display is shown but the separation is not confirmed (see REPORT.md in
// volatility-risk-20261116). The display code keeps that caveat in its note
// text rather than in the forecast object itself.
const UPSET_COMPONENTS = [
  // [components key, ECDF table key, high-side phrase, low-side phrase]
  ['ent_model', 'ent', '予想が割れている', '予想が本命に集中している'],
  ['weak_fav_mkt', 'weak_fav', '人気が割れている', '人気が本命に集中している'],
  ['field', 'field', '出走頭数が多い', '出走頭数が少ない'],
  ['thin_share', 'thin_share', '実績の薄い馬が多い', '実績馬が揃っている'],
  ['weak_ability_conc', 'weak_ab', '能力が拮抗している', '能力上位が抜けている'],
];

export function upsetFromRisk(risk) {
  if (!risk || typeof risk !== 'object') return null;
  const segment = risk.segment;
  const table = RISK_ECDF_TABLES[segment];
  const score = finite(risk.score);
  if (!table || score === null || !risk.components) return null;
  const level = score >= 2 / 3 ? '高' : score >= 1 / 3 ? '中' : '低';
  const ranked = [];
  for (let i = 0; i < UPSET_COMPONENTS.length; i++) {
    const [key, tableKey, highPhrase, lowPhrase] = UPSET_COMPONENTS[i];
    const v = finite(risk.components[key]);
    if (v === null) return null;
    ranked.push({i, e: ecdf(table[tableKey], v), highPhrase, lowPhrase});
  }
  let reasons;
  if (level === '低') {
    const picked = ranked.filter((x) => x.e <= 0.5)
      .sort((a, b) => (a.e - b.e) || (a.i - b.i)).slice(0, 2);
    const list = picked.length ? picked
      : [ranked.slice().sort((a, b) => (a.e - b.e) || (a.i - b.i))[0]];
    reasons = list.map((x) => x.lowPhrase);
  } else {
    const picked = ranked.filter((x) => x.e >= 0.5)
      .sort((a, b) => (b.e - a.e) || (a.i - b.i)).slice(0, 2);
    const list = picked.length ? picked
      : [ranked.slice().sort((a, b) => (b.e - a.e) || (a.i - b.i))[0]];
    reasons = list.map((x) => x.highPhrase);
  }
  return {
    version: UPSET_FORECAST_VERSION,
    level,
    score100: Math.round(score * 100),
    label: risk.label,
    score,
    segment,
    reasons,
  };
}

export function computeUpsetForecast(detail) {
  const risk = computeRiskLabel(detail);
  return risk ? upsetFromRisk(risk) : null;
}
