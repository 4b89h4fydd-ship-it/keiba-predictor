import legacyWorker from "./worker.js";

const SCRATCH_RE = /(?:出走取消|取消|競走除外|競走取消|除外|SCRATCHED)/i;

function overlayHorse(horse, live) {
  if (!horse || !live) return horse;
  const status = String(live.horse_status ?? live.status ?? "").trim();
  const next = { ...horse };
  if (live.win_odds != null) next.winOdds = live.win_odds;
  if (live.popularity != null) next.popularity = live.popularity;
  if (live.body_weight != null) next.bodyWeight = live.body_weight;
  if (live.body_weight_change != null) next.bodyWeightChange = live.body_weight_change;
  if (status) {
    next.status = status;
    next.scratched = SCRATCH_RE.test(status);
  }
  return next;
}

function overlayDetail(detail, liveRows) {
  if (!detail || typeof detail !== "object" || !Array.isArray(detail.horses)) {
    return detail;
  }
  const byNo = new Map();
  for (const row of liveRows || []) {
    const no = Number(row.horse_no ?? row.horseNumber ?? 0);
    if (no > 0) byNo.set(no, row);
  }
  return {
    ...detail,
    horses: detail.horses.map(h => {
      const no = Number(h?.horseNumber ?? h?.horse_no ?? 0);
      return overlayHorse(h, byNo.get(no));
    })
  };
}

function jsonResponse(body, original) {
  const headers = new Headers(original.headers);
  headers.set("content-type", "application/json; charset=utf-8");
  headers.set("cache-control", "no-store");
  return new Response(JSON.stringify(body), {
    status: original.status,
    statusText: original.statusText,
    headers
  });
}

async function oddsForDay(env, date) {
  const result = await env.DB.prepare(`
    SELECT
      o.race_id,
      o.horse_no,
      o.win_odds,
      o.popularity,
      o.body_weight,
      o.body_weight_change,
      o.horse_status,
      o.updated_at
    FROM odds_current o
    INNER JOIN race_summaries r
      ON r.race_id = o.race_id
    WHERE r.race_date = ?
    ORDER BY o.race_id, o.horse_no
  `).bind(date).all();
  return result.results || [];
}

async function enhanceRaceResponse(response) {
  if (!response.ok) return response;
  let body;
  try {
    body = await response.clone().json();
  } catch {
    return response;
  }
  if (!body || typeof body !== "object") return response;
  const odds = Array.isArray(body.odds) ? body.odds : [];
  body.detail = overlayDetail(body.detail, odds);
  return jsonResponse(body, response);
}

async function enhanceDayResponse(response, env, url) {
  if (!response.ok || url.searchParams.get("details") === "0") return response;
  let body;
  try {
    body = await response.clone().json();
  } catch {
    return response;
  }
  if (!body || typeof body !== "object" || !Array.isArray(body.details)) return response;
  const date = url.searchParams.get("date") || "";
  if (!date) return response;
  let liveRows = [];
  try {
    liveRows = await oddsForDay(env, date);
  } catch {
    return response;
  }
  const byRace = new Map();
  for (const row of liveRows) {
    const rid = String(row.race_id || "");
    if (!rid) continue;
    if (!byRace.has(rid)) byRace.set(rid, []);
    byRace.get(rid).push(row);
  }
  body.details = body.details.map(detail => {
    const rid = String(detail?.id ?? detail?.race_id ?? detail?.raceId ?? "");
    return overlayDetail(detail, byRace.get(rid) || []);
  });
  return jsonResponse(body, response);
}

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const response = await legacyWorker.fetch(request, env, ctx);
    if (request.method !== "GET") return response;
    if (url.pathname.startsWith("/api/race/")) {
      return enhanceRaceResponse(response);
    }
    if (url.pathname === "/api/day") {
      return enhanceDayResponse(response, env, url);
    }
    return response;
  }
};
