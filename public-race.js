/* 126: Public race facts cannot restore retired predictions from D1 archives.
 * Raw D1 records and authenticated audit/admin routes are not modified.
 */
export const RETIRED_KEYS = new Set([
  'aiEvaluation','integratedEvaluation','factorRanking','honmeiDecision',
  'preRacePrediction','preRaceBet','predictionAudit','frozenPredictionAudit',
  'winnerLearningProfile','betRecommendations','recommendedBets','tickets','buyList','bets',
  'markMethod','markEngineVersion','predictionModelVersion','mark','predMark','印',
  'honmeiRole','modelProbabilities','forecastRevisions','currentForecastRevisionId',
  'preoffStage64Archive','morningMarkSnapshot','officialMarkRevisions','modelMarkRevisions','savedForecastRevision',
  '_savedPreoffOriginal','legacyPredictionAudit','preRaceAudit','observedModelCoverage'
]);

// Keep only previously computed, race-bound Stage64 products. Do not recompute
// predictions, revive retired models, or promote incomplete saved candidate marks.
export function authorizedStage64(race) {
  const p = race.prediction;
  if (race.predictionStatus !== 'ready' || !p ||
      p.predictionStatus !== 'ready' || p.productionEligible !== true ||
      p.modelVersion !== 'arvexq-stage64-product-v1' ||
      p.raceId !== race.id || p.date !== race.date ||
      !Array.isArray(race.horses) || !Array.isArray(race.predictionMarks) ||
      race.predictionMarks.length !== 5) return null;
  const known = new Set(race.horses.map(h => h?.horseNumber));
  const labels = ['◎','○','▲','△','☆'];
  const used = new Set();
  const marks = [];
  for (let i = 0; i < 5; i++) {
    const row = race.predictionMarks[i];
    if (!row || row.mark !== labels[i] ||
        !Number.isInteger(row.horseNumber) || !known.has(row.horseNumber) ||
        used.has(row.horseNumber)) return null;
    used.add(row.horseNumber);
    marks.push({...row});
  }
  return marks;
}

export function publicRace(value) {
  if (Array.isArray(value)) return value.map(publicRace);
  if (!value || typeof value !== 'object') return value;
  const result = {};
  for (const [key, entry] of Object.entries(value)) {
    if (!RETIRED_KEYS.has(key)) result[key] = publicRace(entry);
  }
  if (Array.isArray(value.horses)) {
    const live = authorizedStage64(value);
    if (live) {
      const byNo = new Map(live.map(row => [row.horseNumber, row.mark]));
      result.predictionStatus = 'ready';
      result.predictionModelVersion = value.prediction.modelVersion;
      result.predictionMarks = live;
      // Tickets belong to the same server-approved Stage64 product as the marks.
      if (Array.isArray(value.recommendedBets)) result.recommendedBets = structuredClone(value.recommendedBets);
      result.horses = result.horses.map(h => ({
        ...h, ...(byNo.has(h.horseNumber) ? {predMark:byNo.get(h.horseNumber)} : {})
      }));
    } else {
      result.predictionStatus = 'disabled';
      result.predictionModelVersion = 'arvexq-prediction-removed';
      delete result.predictionMarks;
      delete result.prediction;
      delete result.recommendedBets;
    }
  }
  return result;
}

export async function publicRaceResponse(response, request) {
  const path = new URL(request.url).pathname;
  if (request.method !== 'GET' || !response.ok ||
      !(path === '/api/day' || path.startsWith('/api/race/') || path.startsWith('/api/racecard/'))) return response;
  let body;
  try { body = await response.clone().json(); }
  catch { return response; }
  const headers = new Headers(response.headers);
  headers.delete('content-length');
  headers.delete('etag');
  headers.set('content-type', 'application/json; charset=utf-8');
  headers.set('cache-control', 'no-store');
  return new Response(JSON.stringify(publicRace(body)), {status:response.status, statusText:response.statusText, headers});
}
