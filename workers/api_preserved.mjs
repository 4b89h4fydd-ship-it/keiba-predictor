var __defProp = Object.defineProperty;
var __name = (target, value) => __defProp(target, "name", { value, configurable: true });

// worker.js
function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: {
      "content-type": "application/json; charset=utf-8",
      "cache-control": "no-store",
      "access-control-allow-origin": "*",
      "access-control-allow-headers": "content-type, authorization, x-sync-token",
      "access-control-allow-methods": "GET,POST,OPTIONS"
    }
  });
}
__name(json, "json");
function safeJson(text) {
  try {
    return text ? JSON.parse(text) : null;
  } catch {
    return null;
  }
}
__name(safeJson, "safeJson");
function first(obj, ...keys) {
  for (const key of keys) {
    const value = obj?.[key];
    if (value !== void 0 && value !== null && value !== "") {
      return value;
    }
  }
  return null;
}
__name(first, "first");
function asInt(value, fallback = 0) {
  const n = Number(value);
  return Number.isFinite(n) ? Math.trunc(n) : fallback;
}
__name(asInt, "asInt");
function asNum(value) {
  if (value === null || value === void 0 || value === "") {
    return null;
  }
  const n = Number(value);
  return Number.isFinite(n) ? n : null;
}
__name(asNum, "asNum");
function nowSec() {
  return Math.floor(Date.now() / 1e3);
}
__name(nowSec, "nowSec");
function authorized(request, env) {
  if (!env.SYNC_TOKEN) return false;
  const bearer = request.headers.get("authorization") || "";
  const headerToken = request.headers.get("x-sync-token") || "";
  return bearer === `Bearer ${env.SYNC_TOKEN}` || headerToken === env.SYNC_TOKEN;
}
__name(authorized, "authorized");
async function runBatches(db, statements, size = 75) {
  const results = [];
  for (let i = 0; i < statements.length; i += size) {
    const chunk = statements.slice(i, i + size);
    if (chunk.length) {
      results.push(...await db.batch(chunk));
    }
  }
  return results;
}
__name(runBatches, "runBatches");
var worker_default = {
  async fetch(request, env) {
    const url = new URL(request.url);
    const path = url.pathname;
    if (request.method === "OPTIONS") {
      return new Response(null, {
        status: 204
      });
    }
    try {
      if (path === "/api/health") {
        return json({
          ok: true,
          service: "KRAIZ API",
          version: "cloudflare-api-v3-sync"
        });
      }
      if (path === "/api/db-check") {
        const result = await env.DB.prepare(`
          SELECT name
          FROM sqlite_master
          WHERE type = 'table'
          ORDER BY name
        `).all();
        return json({
          ok: true,
          tables: result.results || []
        });
      }
      if (path === "/api/races") {
        const date = url.searchParams.get("date");
        if (!date) {
          return json({
            ok: false,
            error: "date is required"
          }, 400);
        }
        const result = await env.DB.prepare(`
          SELECT
            race_id,
            race_date,
            circuit,
            track,
            race_no,
            start_time,
            title,
            surface,
            distance,
            weather,
            condition,
            volatility_label,
            volatility_score,
            race_status,
            updated_at
          FROM race_summaries
          WHERE race_date = ?
          ORDER BY circuit, track, race_no
        `).bind(date).all();
        return json({
          ok: true,
          date,
          races: result.results || []
        });
      }
      if (path === "/api/day") {
        const date = url.searchParams.get("date");
        const includeDetails = url.searchParams.get("details") !== "0";
        if (!date) {
          return json({
            ok: false,
            error: "date is required"
          }, 400);
        }
        const summaryResult = await env.DB.prepare(`
    SELECT *
    FROM race_summaries
    WHERE race_date = ?
    ORDER BY circuit, track, race_no
  `).bind(date).all();
        const races = (summaryResult.results || []).map(
          (r) => ({
            id: r.race_id,
            date: r.race_date,
            circuit: r.circuit,
            track: r.track,
            raceNumber: r.race_no,
            startTime: r.start_time,
            scheduledStartTime: r.start_time,
            title: r.title,
            surface: r.surface,
            distance: r.distance,
            weather: r.weather,
            condition: r.condition,
            volatility: {
              label: r.volatility_label || "",
              score: r.volatility_score
            },
            raceStatus: r.race_status || "",
            updatedAtEpoch: r.updated_at
          })
        );
        if (!includeDetails) {
          return json({
            ok: true,
            date,
            races,
            details: [],
            raceCount: races.length,
            detailCount: 0,
            analysisCount: 0,
            missing: [],
            complete: races.length > 0,
            displayComplete: races.length > 0,
            source: "cloudflare-d1"
          });
        }
        const detailResult = await env.DB.prepare(`
    SELECT
      race_id,
      payload,
      analysis_ready,
      updated_at
    FROM race_details
    WHERE race_date = ?
    ORDER BY race_id
  `).bind(date).all();
        const detailRows = detailResult.results || [];
        const details = detailRows.map((r) => safeJson(r.payload)).filter(Boolean);
        const detailIds = new Set(
          details.map(
            (d) => String(d.id || d.race_id || d.raceId || "")
          )
        );
        const missing = races.map((r) => String(r.id || "")).filter((id) => id && !detailIds.has(id));
        const analysisCount = detailRows.filter(
          (r) => Number(r.analysis_ready || 0) === 1
        ).length;
        const complete = races.length > 0 && missing.length === 0;
        return json({
          ok: true,
          date,
          races,
          details,
          raceCount: races.length,
          detailCount: details.length,
          analysisCount,
          missing,
          complete,
          displayComplete: complete,
          analysisComplete: complete && analysisCount >= races.length,
          source: "cloudflare-d1"
        });
      }
      if (path.startsWith("/api/race/")) {
        const raceId = decodeURIComponent(
          path.substring("/api/race/".length)
        );
        if (!raceId) {
          return json({
            ok: false,
            error: "race_id is required"
          }, 400);
        }
        const detail = await env.DB.prepare(`
          SELECT
            race_id,
            race_date,
            payload,
            analysis_ready,
            updated_at
          FROM race_details
          WHERE race_id = ?
          LIMIT 1
        `).bind(raceId).first();
        if (!detail) {
          return json({
            ok: false,
            error: "race not found",
            race_id: raceId
          }, 404);
        }
        const summary = await env.DB.prepare(`
          SELECT *
          FROM race_summaries
          WHERE race_id = ?
          LIMIT 1
        `).bind(raceId).first();
        const odds = await env.DB.prepare(`
          SELECT
            horse_no,
            win_odds,
            popularity,
            body_weight,
            body_weight_change,
            horse_status,
            updated_at
          FROM odds_current
          WHERE race_id = ?
          ORDER BY horse_no
        `).bind(raceId).all();
        return json({
          ok: true,
          race_id: raceId,
          summary: summary || null,
          detail: safeJson(detail.payload),
          analysis_ready: !!detail.analysis_ready,
          detail_updated_at: detail.updated_at,
          odds: odds.results || []
        });
      }
      if (path.startsWith("/api/odds/")) {
        const raceId = decodeURIComponent(
          path.substring("/api/odds/".length)
        );
        const result = await env.DB.prepare(`
          SELECT
            horse_no,
            win_odds,
            popularity,
            body_weight,
            body_weight_change,
            horse_status,
            updated_at
          FROM odds_current
          WHERE race_id = ?
          ORDER BY horse_no
        `).bind(raceId).all();
        return json({
          ok: true,
          race_id: raceId,
          odds: result.results || []
        });
      }
      if (path === "/api/sync") {
        if (request.method !== "POST") {
          return json({
            ok: false,
            error: "POST required"
          }, 405);
        }
        if (!authorized(request, env)) {
          const expectedLength = String(env.SYNC_TOKEN || "").trim().length;
          const headerLength = String(
            request.headers.get("x-sync-token") || ""
          ).trim().length;
          return json({
            ok: false,
            error: "unauthorized",
            debug: {
              cloudflare_token_length: expectedLength,
              github_token_length: headerLength
            }
          }, 401);
        }
        const body = await request.json();
        const summaries = Array.isArray(body.summaries) ? body.summaries : Array.isArray(body.races) ? body.races : [];
        const details = Array.isArray(body.details) ? body.details : Array.isArray(body.raceDetails) ? body.raceDetails : [];
        const oddsCurrent = Array.isArray(body.odds_current) ? body.odds_current : Array.isArray(body.oddsCurrent) ? body.oddsCurrent : [];
        const oddsHistory = Array.isArray(body.odds_history) ? body.odds_history : Array.isArray(body.oddsHistory) ? body.oddsHistory : [];
        const meta = body.meta && typeof body.meta === "object" ? body.meta : {};
        const syncedAt = nowSec();
        const summaryStatements = [];
        for (const row of summaries) {
          const raceId = String(
            first(
              row,
              "race_id",
              "raceId",
              "id"
            ) || ""
          );
          const raceDate = String(
            first(
              row,
              "race_date",
              "raceDate",
              "date"
            ) || ""
          );
          if (!raceId || !raceDate) {
            continue;
          }
          const volatility = row.volatility && typeof row.volatility === "object" ? row.volatility : {};
          const volatilityLabel = first(
            row,
            "volatility_label",
            "volatilityLabel"
          ) ?? first(volatility, "label");
          const volatilityScore = first(
            row,
            "volatility_score",
            "volatilityScore"
          ) ?? first(volatility, "score");
          summaryStatements.push(
            env.DB.prepare(`
              INSERT INTO race_summaries (
                race_id,
                race_date,
                circuit,
                track,
                race_no,
                start_time,
                title,
                surface,
                distance,
                weather,
                condition,
                volatility_label,
                volatility_score,
                race_status,
                updated_at
              )
              VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?, ?
              )

              ON CONFLICT(race_id)
              DO UPDATE SET
                race_date =
                  excluded.race_date,
                circuit =
                  excluded.circuit,
                track =
                  excluded.track,
                race_no =
                  excluded.race_no,
                start_time =
                  excluded.start_time,
                title =
                  excluded.title,
                surface =
                  excluded.surface,
                distance =
                  excluded.distance,
                weather =
                  excluded.weather,
                condition =
                  excluded.condition,
                volatility_label =
                  excluded.volatility_label,
                volatility_score =
                  excluded.volatility_score,
                race_status =
                  excluded.race_status,
                updated_at =
                  excluded.updated_at
            `).bind(
              raceId,
              raceDate,
              String(
                first(row, "circuit") || ""
              ),
              String(
                first(row, "track") || ""
              ),
              asInt(
                first(
                  row,
                  "race_no",
                  "raceNo",
                  "raceNumber"
                )
              ),
              String(
                first(
                  row,
                  "start_time",
                  "startTime",
                  "scheduledStartTime"
                ) || ""
              ),
              String(
                first(row, "title") || ""
              ),
              String(
                first(row, "surface") || ""
              ),
              asInt(
                first(row, "distance")
              ),
              String(
                first(row, "weather") || ""
              ),
              String(
                first(row, "condition") || ""
              ),
              volatilityLabel == null ? "" : String(volatilityLabel),
              volatilityScore == null ? null : asInt(volatilityScore),
              String(
                first(
                  row,
                  "race_status",
                  "raceStatus",
                  "status"
                ) || ""
              ),
              asInt(
                first(
                  row,
                  "updated_at",
                  "updatedAt",
                  "updatedAtEpoch"
                ),
                syncedAt
              )
            )
          );
        }
        const detailStatements = [];
        for (const row of details) {
          const payloadObject = row.payload ?? row.detail ?? row;
          const raceId = String(
            first(
              row,
              "race_id",
              "raceId",
              "id"
            ) || first(
              payloadObject,
              "race_id",
              "raceId",
              "id"
            ) || ""
          );
          const raceDate = String(
            first(
              row,
              "race_date",
              "raceDate",
              "date"
            ) || first(
              payloadObject,
              "race_date",
              "raceDate",
              "date"
            ) || ""
          );
          if (!raceId || !raceDate) {
            continue;
          }
          const analysisReadyRaw = first(
            row,
            "analysis_ready",
            "analysisReady"
          ) ?? first(
            payloadObject?.preparedMeta || {},
            "diagnosisReady"
          );
          const analysisReady = analysisReadyRaw ? 1 : 0;
          const payloadText = typeof row.payload === "string" ? row.payload : JSON.stringify(payloadObject);
          detailStatements.push(
            env.DB.prepare(`
              INSERT INTO race_details (
                race_id,
                race_date,
                payload,
                analysis_ready,
                updated_at
              )
              VALUES (?, ?, ?, ?, ?)

              ON CONFLICT(race_id)
              DO UPDATE SET
                race_date =
                  excluded.race_date,
                payload =
                  excluded.payload,
                analysis_ready =
                  excluded.analysis_ready,
                updated_at =
                  excluded.updated_at
            `).bind(
              raceId,
              raceDate,
              payloadText,
              analysisReady,
              asInt(
                first(
                  row,
                  "updated_at",
                  "updatedAt",
                  "updatedAtEpoch"
                ),
                syncedAt
              )
            )
          );
        }
        const currentStatements = [];
        for (const row of oddsCurrent) {
          const raceId = String(
            first(
              row,
              "race_id",
              "raceId"
            ) || ""
          );
          const horseNo = asInt(
            first(
              row,
              "horse_no",
              "horseNo",
              "horseNumber"
            )
          );
          if (!raceId || horseNo <= 0) {
            continue;
          }
          currentStatements.push(
            env.DB.prepare(`
              INSERT INTO odds_current (
                race_id,
                horse_no,
                win_odds,
                popularity,
                body_weight,
                body_weight_change,
                horse_status,
                updated_at
              )
              VALUES (?, ?, ?, ?, ?, ?, ?, ?)

              ON CONFLICT(race_id, horse_no)
              DO UPDATE SET
                win_odds =
                  excluded.win_odds,
                popularity =
                  excluded.popularity,
                body_weight =
                  excluded.body_weight,
                body_weight_change =
                  excluded.body_weight_change,
                horse_status =
                  excluded.horse_status,
                updated_at =
                  excluded.updated_at
            `).bind(
              raceId,
              horseNo,
              asNum(
                first(
                  row,
                  "win_odds",
                  "winOdds"
                )
              ),
              first(
                row,
                "popularity"
              ) == null ? null : asInt(
                first(row, "popularity")
              ),
              first(
                row,
                "body_weight",
                "bodyWeight"
              ) == null ? null : asInt(
                first(
                  row,
                  "body_weight",
                  "bodyWeight"
                )
              ),
              first(
                row,
                "body_weight_change",
                "bodyWeightChange"
              ) == null ? null : asInt(
                first(
                  row,
                  "body_weight_change",
                  "bodyWeightChange"
                )
              ),
              String(
                first(
                  row,
                  "horse_status",
                  "horseStatus",
                  "status"
                ) || ""
              ),
              asInt(
                first(
                  row,
                  "updated_at",
                  "updatedAt"
                ),
                syncedAt
              )
            )
          );
        }
        const historyStatements = [];
        for (const row of oddsHistory) {
          const raceId = String(
            first(
              row,
              "race_id",
              "raceId"
            ) || ""
          );
          const horseNo = asInt(
            first(
              row,
              "horse_no",
              "horseNo",
              "horseNumber"
            )
          );
          const capturedAt = asInt(
            first(
              row,
              "captured_at",
              "capturedAt"
            ),
            syncedAt
          );
          if (!raceId || horseNo <= 0) {
            continue;
          }
          historyStatements.push(
            env.DB.prepare(`
              INSERT INTO odds_history (
                race_id,
                horse_no,
                win_odds,
                popularity,
                captured_at
              )

              SELECT ?, ?, ?, ?, ?

              WHERE NOT EXISTS (
                SELECT 1
                FROM odds_history
                WHERE race_id = ?
                  AND horse_no = ?
                  AND captured_at = ?
              )
            `).bind(
              raceId,
              horseNo,
              asNum(
                first(
                  row,
                  "win_odds",
                  "winOdds"
                )
              ),
              first(
                row,
                "popularity"
              ) == null ? null : asInt(
                first(row, "popularity")
              ),
              capturedAt,
              raceId,
              horseNo,
              capturedAt
            )
          );
        }
        const metaStatements = [];
        for (const [key, value] of Object.entries(meta)) {
          metaStatements.push(
            env.DB.prepare(`
              INSERT INTO meta (
                key,
                value,
                updated_at
              )
              VALUES (?, ?, ?)

              ON CONFLICT(key)
              DO UPDATE SET
                value =
                  excluded.value,
                updated_at =
                  excluded.updated_at
            `).bind(
              String(key),
              typeof value === "string" ? value : JSON.stringify(value),
              syncedAt
            )
          );
        }
        metaStatements.push(
          env.DB.prepare(`
            INSERT INTO meta (
              key,
              value,
              updated_at
            )
            VALUES (
              'last_sync_at',
              ?,
              ?
            )

            ON CONFLICT(key)
            DO UPDATE SET
              value =
                excluded.value,
              updated_at =
                excluded.updated_at
          `).bind(
            String(syncedAt),
            syncedAt
          )
        );
        await runBatches(
          env.DB,
          summaryStatements
        );
        await runBatches(
          env.DB,
          detailStatements
        );
        await runBatches(
          env.DB,
          currentStatements
        );
        await runBatches(
          env.DB,
          historyStatements
        );
        await runBatches(
          env.DB,
          metaStatements
        );
        return json({
          ok: true,
          synced_at: syncedAt,
          received: {
            summaries: summaries.length,
            details: details.length,
            odds_current: oddsCurrent.length,
            odds_history: oddsHistory.length,
            meta: Object.keys(meta).length
          },
          written: {
            summaries: summaryStatements.length,
            details: detailStatements.length,
            odds_current: currentStatements.length,
            odds_history: historyStatements.length,
            meta: metaStatements.length
          }
        });
      }
      return json({
        ok: true,
        service: "KRAIZ API",
        endpoints: [
          "/api/health",
          "/api/db-check",
          "/api/races?date=YYYY-MM-DD",
          "/api/race/<race_id>",
          "/api/odds/<race_id>",
          "POST /api/sync"
        ]
      });
    } catch (err) {
      return json({
        ok: false,
        error: String(
          err?.message || err
        )
      }, 500);
    }
  }
};

// racecard.js
var BASIC_SQL = `
  SELECT json_object(
    'id', race_id, 'date', race_date,
    'track', json_extract(payload, '$.track'),
    'circuit', json_extract(payload, '$.circuit'),
    'raceNumber', json_extract(payload, '$.raceNumber'),
    'title', json_extract(payload, '$.title'),
    'distance', json_extract(payload, '$.distance'),
    'surface', json_extract(payload, '$.surface'),
    'startTime', json_extract(payload, '$.startTime'),
    'fieldSize', json_extract(payload, '$.fieldSize'),
    'weather', json_extract(payload, '$.weather'),
    'condition', json_extract(payload, '$.condition'),
    'raceStatus', json_extract(payload, '$.raceStatus')
  ) AS basic FROM race_details
  WHERE race_id = ? AND json_valid(payload) = 1 LIMIT 1`;
var HORSES_SQL = `
  SELECT json_object(
    'horseNumber', json_extract(h.value, '$.horseNumber'),
    'frameNumber', json_extract(h.value, '$.frameNumber'),
    'name', json_extract(h.value, '$.name'),
    'sex', json_extract(h.value, '$.sex'),
    'age', json_extract(h.value, '$.age'),
    'jockey', json_extract(h.value, '$.jockey'),
    'trainer', json_extract(h.value, '$.trainer'),
    'carriedWeight', json_extract(h.value, '$.carriedWeight'),
    'bodyWeight', json_extract(h.value, '$.bodyWeight'),
    'bodyWeightChange', json_extract(h.value, '$.bodyWeightChange'),
    'winOdds', json_extract(h.value, '$.winOdds'),
    'popularity', json_extract(h.value, '$.popularity'),
    'status', json_extract(h.value, '$.status'),
    'scratched', json_extract(h.value, '$.scratched'),
    'withdrawn', json_extract(h.value, '$.withdrawn')
  ) AS horse
  FROM race_details r, json_each(r.payload, '$.horses') h
  WHERE r.race_id = ? AND json_valid(r.payload) = 1
    AND CAST(json_extract(h.value, '$.horseNumber') AS INTEGER) > 0
  ORDER BY CAST(json_extract(h.value, '$.horseNumber') AS INTEGER)`;
async function readRacecard(env, raceId) {
  const response = /* @__PURE__ */ __name((body, status = 200) => new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json; charset=utf-8", "cache-control": "no-store" }
  }), "response");
  if (!raceId) return response({ ok: false, error: "race_id is required" }, 400);
  try {
    const row = await env.DB.prepare(BASIC_SQL).bind(raceId).first();
    if (!row) return response({ ok: false, error: "race not found", race_id: raceId }, 404);
    const basic = JSON.parse(row.basic);
    const result = await env.DB.prepare(HORSES_SQL).bind(raceId).all();
    const horses = (result.results || []).map((row2) => {
      const h = JSON.parse(row2.horse);
      h.scratched = h.scratched === true || h.scratched === 1;
      h.withdrawn = h.withdrawn === true || h.withdrawn === 1;
      return h;
    });
    return response({
      ok: true,
      race_id: raceId,
      summary: basic,
      detail: { ...basic, horses, _entryOnly: true },
      entry_state: horses.length ? "loaded" : basic.fieldSize === 0 ? "empty" : "loading"
    });
  } catch {
    return response({ ok: false, error: "racecard temporarily unavailable", race_id: raceId }, 503);
  }
}
__name(readRacecard, "readRacecard");
var DISPLAY_SQL = `SELECT
  json_remove(payload, '$.massFeatureSnapshot') AS payload,
  analysis_ready, updated_at
  FROM race_details WHERE race_id = ? AND json_valid(payload) = 1 LIMIT 1`;
async function readRaceDisplay(env, raceId) {
  const response = /* @__PURE__ */ __name((body, status = 200) => new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json; charset=utf-8", "cache-control": "no-store" }
  }), "response");
  if (!raceId) return response({ ok: false, error: "race_id is required" }, 400);
  try {
    const row = await env.DB.prepare(DISPLAY_SQL).bind(raceId).first();
    if (!row) return response({ ok: false, error: "race not found", race_id: raceId }, 404);
    const detail = JSON.parse(row.payload);
    let odds = [];
    try {
      const result = await env.DB.prepare(`SELECT horse_no, win_odds, popularity,
        body_weight, body_weight_change, horse_status, updated_at
        FROM odds_current WHERE race_id = ? ORDER BY horse_no`).bind(raceId).all();
      odds = result.results || [];
    } catch {
    }
    return response({
      ok: true,
      race_id: raceId,
      detail,
      summary: {
        id: raceId,
        date: detail.date,
        track: detail.track,
        raceNumber: detail.raceNumber
      },
      analysis_ready: !!row.analysis_ready,
      detail_updated_at: row.updated_at,
      odds
    });
  } catch {
    return response({ ok: false, error: "race detail temporarily unavailable", race_id: raceId }, 503);
  }
}
__name(readRaceDisplay, "readRaceDisplay");

// worker-entry.js
var SCRATCH_RE = /(?:出走取消|取消|競走除外|競走取消|除外|SCRATCHED)/i;
var CORS_ALLOW_HEADERS = "content-type, authorization, x-sync-token, cache-control, pragma, accept";
var CORS_ALLOW_METHODS = "GET,POST,OPTIONS";
function corsHeaders(request) {
  const requested = String(request?.headers?.get("access-control-request-headers") || "").trim();
  return {
    "access-control-allow-origin": "*",
    "access-control-allow-methods": CORS_ALLOW_METHODS,
    "access-control-allow-headers": requested || CORS_ALLOW_HEADERS,
    "access-control-max-age": "86400",
    "vary": "Origin, Access-Control-Request-Headers"
  };
}
__name(corsHeaders, "corsHeaders");
function withCors(response, request) {
  const headers = new Headers(response.headers);
  const cors = corsHeaders(request);
  for (const [key, value] of Object.entries(cors)) headers.set(key, value);
  return new Response(response.body, {
    status: response.status,
    statusText: response.statusText,
    headers
  });
}
__name(withCors, "withCors");
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
__name(overlayHorse, "overlayHorse");
function overlayDetail(detail, liveRows) {
  if (!detail || typeof detail !== "object" || !Array.isArray(detail.horses)) {
    return detail;
  }
  const byNo = /* @__PURE__ */ new Map();
  for (const row of liveRows || []) {
    const no = Number(row.horse_no ?? row.horseNumber ?? 0);
    if (no > 0) byNo.set(no, row);
  }
  return {
    ...detail,
    horses: detail.horses.map((h) => {
      const no = Number(h?.horseNumber ?? h?.horse_no ?? 0);
      return overlayHorse(h, byNo.get(no));
    })
  };
}
__name(overlayDetail, "overlayDetail");
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
__name(jsonResponse, "jsonResponse");
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
__name(oddsForDay, "oddsForDay");
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
__name(enhanceRaceResponse, "enhanceRaceResponse");
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
  const byRace = /* @__PURE__ */ new Map();
  for (const row of liveRows) {
    const rid = String(row.race_id || "");
    if (!rid) continue;
    if (!byRace.has(rid)) byRace.set(rid, []);
    byRace.get(rid).push(row);
  }
  body.details = body.details.map((detail) => {
    const rid = String(detail?.id ?? detail?.race_id ?? detail?.raceId ?? "");
    return overlayDetail(detail, byRace.get(rid) || []);
  });
  return jsonResponse(body, response);
}
__name(enhanceDayResponse, "enhanceDayResponse");
var worker_entry_default = {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    if (request.method === "OPTIONS") {
      return new Response(null, {
        status: 204,
        headers: corsHeaders(request)
      });
    }
    if (request.method === "GET" && url.pathname.startsWith("/api/racecard/")) {
      let raceId;
      try {
        raceId = decodeURIComponent(url.pathname.slice("/api/racecard/".length));
      } catch {
        return withCors(new Response('{"ok":false,"error":"invalid race_id"}', { status: 400, headers: { "content-type": "application/json" } }), request);
      }
      return withCors(await readRacecard(env, raceId), request);
    }
    if (request.method === "GET" && url.pathname.startsWith("/api/race/") && url.searchParams.get("view") === "display") {
      let raceId;
      try {
        raceId = decodeURIComponent(url.pathname.slice("/api/race/".length));
      } catch {
        return withCors(new Response('{"ok":false,"error":"invalid race_id"}', { status: 400, headers: { "content-type": "application/json" } }), request);
      }
      return withCors(await readRaceDisplay(env, raceId), request);
    }
    let response = await worker_default.fetch(request, env, ctx);
    if (request.method === "GET") {
      if (url.pathname.startsWith("/api/race/")) {
        response = await enhanceRaceResponse(response);
      } else if (url.pathname === "/api/day") {
        response = await enhanceDayResponse(response, env, url);
      }
    }
    return withCors(response, request);
  }
};
export {
  worker_entry_default as default
};
//# sourceMappingURL=worker-entry.js.map
