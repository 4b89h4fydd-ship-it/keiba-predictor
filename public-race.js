/* 126: Public race facts cannot restore retired predictions from D1 archives.
 * Raw D1 records and authenticated audit/admin routes are not modified.
 */
export const RETIRED_KEYS = new Set([
  'aiEvaluation','integratedEvaluation','factorRanking','honmeiDecision',
  'preRacePrediction','preRaceBet','predictionAudit','frozenPredictionAudit',
  'winnerLearningProfile','betRecommendations','recommendedBets','tickets','buyList','bets',
  'markMethod','markEngineVersion','predictionModelVersion','mark','predMark','印',
  'honmeiRole','modelProbabilities','forecastRevisions','currentForecastRevisionId',
  'morningMarkSnapshot','officialMarkRevisions','modelMarkRevisions','savedForecastRevision',
  '_savedPreoffOriginal','legacyPredictionAudit','preRaceAudit','observedModelCoverage'
]);

export function publicRace(value, path = '') {
  if (Array.isArray(value)) return value.map(entry => publicRace(entry, path));
  if (!value || typeof value !== 'object') return value;
  const result = {};
  for (const [key, entry] of Object.entries(value)) {
    // Preserve only the Stage64 six-stage tickets node in the existing
    // researchShadow container; all legacy public bet keys stay retired.
    // The normal public projection used to delete this stage and consequently
    // the client suppressed the *entire* current prediction.
    const stage64Tickets = key === 'tickets' &&
      path.endsWith('/researchShadow/stage64/stages');
    if (!RETIRED_KEYS.has(key) || stage64Tickets)
      result[key] = publicRace(entry, path + '/' + key);
  }
  if (Array.isArray(value.horses)) {
    result.predictionStatus = 'disabled';
    result.predictionModelVersion = 'arvexq-prediction-removed';
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
