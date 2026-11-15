// Display-only environment/odds freshness overlay for the API worker.
//
// Root cause of the two display defects: the per-race detail payload is a
// snapshot built before race-day weather/going is published, so its
// weather/condition stay "不明" and its oddsUpdatedAt stays at build time,
// while race_summaries and odds_current keep being refreshed by live sync.
// The sealed forecast inside the payload is never touched; only the
// top-level display fields of the *response* are reconciled with the live
// stores (race_summaries is the single source for weather/condition, and
// odds_current — the same rows whose winOdds are displayed — is the source
// for oddsUpdatedAt). Stored D1 payloads are never rewritten here.

const UNKNOWN = '不明';

function validEnv(value) {
  return typeof value === 'string' && value !== '' && value !== UNKNOWN;
}

function jstClock(epochSeconds) {
  const parts = new Intl.DateTimeFormat('en-GB', {
    timeZone: 'Asia/Tokyo',
    hourCycle: 'h23',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  }).formatToParts(new Date(epochSeconds * 1000));
  const pick = (type) => parts.find((p) => p.type === type)?.value ?? '00';
  return `${pick('hour')}:${pick('minute')}:${pick('second')}`;
}

// Patch one detail object in place from a summary row and the newest
// odds_current capture epoch for the race (null when no live rows exist).
export function overlayDisplayFields(detail, summary, oddsMaxUpdatedAt) {
  if (!detail || typeof detail !== 'object') return detail;
  if (summary && typeof summary === 'object') {
    if (validEnv(summary.weather)) detail.weather = summary.weather;
    if (validEnv(summary.condition)) detail.condition = summary.condition;
  }
  if (Number.isFinite(oddsMaxUpdatedAt) && oddsMaxUpdatedAt > 0) {
    detail.oddsUpdatedAt = jstClock(oddsMaxUpdatedAt);
  }
  return detail;
}

function maxOddsEpoch(rows) {
  let max = 0;
  for (const row of rows || []) {
    const at = Number(row?.updated_at ?? row?.updatedAt ?? 0);
    if (Number.isFinite(at) && at > max) max = at;
  }
  return max > 0 ? max : null;
}

function jsonResponse(body, original) {
  const headers = new Headers(original.headers);
  headers.set('content-type', 'application/json; charset=utf-8');
  headers.set('cache-control', 'no-store');
  headers.delete('content-length');
  return new Response(JSON.stringify(body), {
    status: original.status,
    statusText: original.statusText,
    headers,
  });
}

// GET /api/race/<id>: body is {summary, detail, odds, ...}. The summary and
// odds rows travel with the response, so no extra storage reads are needed.
export async function overlayRaceResponse(response) {
  if (!response.ok) return response;
  let body;
  try {
    body = await response.clone().json();
  } catch {
    return response;
  }
  if (!body || typeof body !== 'object' || !body.detail) return response;
  overlayDisplayFields(body.detail, body.summary, maxOddsEpoch(body.odds));
  return jsonResponse(body, response);
}

// GET /api/day?details!=0: body is {races: [summary...], details: [...]}.
// Weather/condition come from the summaries in the same body; the newest
// odds capture per race needs one aggregate read of odds_current.
export async function overlayDayResponse(response, env, url) {
  if (!response.ok || url.searchParams.get('details') === '0') return response;
  const date = url.searchParams.get('date') || '';
  if (!date) return response;
  let body;
  try {
    body = await response.clone().json();
  } catch {
    return response;
  }
  if (!body || typeof body !== 'object' || !Array.isArray(body.details)) return response;
  const summaries = new Map();
  for (const race of body.races || []) {
    if (race && race.id) summaries.set(String(race.id), race);
  }
  let oddsMax = new Map();
  try {
    const result = await env.DB.prepare(`
      SELECT o.race_id AS race_id, MAX(o.updated_at) AS max_at
      FROM odds_current o
      INNER JOIN race_summaries r ON r.race_id = o.race_id
      WHERE r.race_date = ?
      GROUP BY o.race_id
    `).bind(date).all();
    for (const row of result.results || []) {
      oddsMax.set(String(row.race_id), Number(row.max_at) || null);
    }
  } catch {
    oddsMax = new Map();
  }
  for (const detail of body.details) {
    const rid = String(detail?.id ?? detail?.race_id ?? detail?.raceId ?? '');
    if (!rid) continue;
    overlayDisplayFields(detail, summaries.get(rid), oddsMax.get(rid) ?? null);
  }
  return jsonResponse(body, response);
}
