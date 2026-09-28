function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: {
      "content-type": "application/json; charset=utf-8",
      "cache-control": "no-store",
      "access-control-allow-origin": "*",
      "access-control-allow-headers":
        "content-type, authorization, x-sync-token",
      "access-control-allow-methods": "GET,POST,OPTIONS"
    }
  });
}

function safeJson(text) {
  try {
    return text ? JSON.parse(text) : null;
  } catch {
    return null;
  }
}

function first(obj, ...keys) {
  for (const key of keys) {
    const value = obj?.[key];
    if (
      value !== undefined &&
      value !== null &&
      value !== ""
    ) {
      return value;
    }
  }
  return null;
}

function asInt(value, fallback = 0) {
  const n = Number(value);
  return Number.isFinite(n) ? Math.trunc(n) : fallback;
}

function asNum(value) {
  if (
    value === null ||
    value === undefined ||
    value === ""
  ) {
    return null;
  }

  const n = Number(value);
  return Number.isFinite(n) ? n : null;
}

function nowSec() {
  return Math.floor(Date.now() / 1000);
}

function authorized(request, env) {
  if (!env.SYNC_TOKEN) return false;

  const bearer =
    request.headers.get("authorization") || "";

  const headerToken =
    request.headers.get("x-sync-token") || "";

  return (
    bearer === `Bearer ${env.SYNC_TOKEN}` ||
    headerToken === env.SYNC_TOKEN
  );
}

async function runBatches(
  db,
  statements,
  size = 75
) {
  const results = [];

  for (
    let i = 0;
    i < statements.length;
    i += size
  ) {
    const chunk = statements.slice(i, i + size);

    if (chunk.length) {
      results.push(...await db.batch(chunk));
    }
  }

  return results;
}

export default {
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
        const date =
          url.searchParams.get("date");

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
        `)
          .bind(date)
          .all();

        return json({
          ok: true,
          date,
          races: result.results || []
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
        `)
          .bind(raceId)
          .first();

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
        `)
          .bind(raceId)
          .first();

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
        `)
          .bind(raceId)
          .all();

        return json({
          ok: true,
          race_id: raceId,
          summary: summary || null,
          detail: safeJson(detail.payload),
          analysis_ready:
            !!detail.analysis_ready,
          detail_updated_at:
            detail.updated_at,
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
        `)
          .bind(raceId)
          .all();

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
  const expectedLength =
    String(env.SYNC_TOKEN || "").trim().length;

  const headerLength =
    String(
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

        const summaries =
          Array.isArray(body.summaries)
            ? body.summaries
            : (
              Array.isArray(body.races)
                ? body.races
                : []
            );

        const details =
          Array.isArray(body.details)
            ? body.details
            : (
              Array.isArray(body.raceDetails)
                ? body.raceDetails
                : []
            );

        const oddsCurrent =
          Array.isArray(body.odds_current)
            ? body.odds_current
            : (
              Array.isArray(body.oddsCurrent)
                ? body.oddsCurrent
                : []
            );

        const oddsHistory =
          Array.isArray(body.odds_history)
            ? body.odds_history
            : (
              Array.isArray(body.oddsHistory)
                ? body.oddsHistory
                : []
            );

        const meta =
          body.meta &&
          typeof body.meta === "object"
            ? body.meta
            : {};

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

          const volatility =
            row.volatility &&
            typeof row.volatility === "object"
              ? row.volatility
              : {};

          const volatilityLabel =
            first(
              row,
              "volatility_label",
              "volatilityLabel"
            ) ??
            first(volatility, "label");

          const volatilityScore =
            first(
              row,
              "volatility_score",
              "volatilityScore"
            ) ??
            first(volatility, "score");

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
              volatilityLabel == null
                ? ""
                : String(volatilityLabel),
              volatilityScore == null
                ? null
                : asInt(volatilityScore),
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
          const payloadObject =
            row.payload ??
            row.detail ??
            row;

          const raceId = String(
            first(
              row,
              "race_id",
              "raceId",
              "id"
            ) ||
            first(
              payloadObject,
              "race_id",
              "raceId",
              "id"
            ) ||
            ""
          );

          const raceDate = String(
            first(
              row,
              "race_date",
              "raceDate",
              "date"
            ) ||
            first(
              payloadObject,
              "race_date",
              "raceDate",
              "date"
            ) ||
            ""
          );

          if (!raceId || !raceDate) {
            continue;
          }

          const analysisReadyRaw =
            first(
              row,
              "analysis_ready",
              "analysisReady"
            ) ??
            first(
              payloadObject?.preparedMeta || {},
              "diagnosisReady"
            );

          const analysisReady =
            analysisReadyRaw ? 1 : 0;

          const payloadText =
            typeof row.payload === "string"
              ? row.payload
              : JSON.stringify(payloadObject);

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
              ) == null
                ? null
                : asInt(
                  first(row, "popularity")
                ),
              first(
                row,
                "body_weight",
                "bodyWeight"
              ) == null
                ? null
                : asInt(
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
              ) == null
                ? null
                : asInt(
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
              ) == null
                ? null
                : asInt(
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

        for (
          const [key, value]
          of Object.entries(meta)
        ) {
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
              typeof value === "string"
                ? value
                : JSON.stringify(value),
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
            summaries:
              summaries.length,
            details:
              details.length,
            odds_current:
              oddsCurrent.length,
            odds_history:
              oddsHistory.length,
            meta:
              Object.keys(meta).length
          },
          written: {
            summaries:
              summaryStatements.length,
            details:
              detailStatements.length,
            odds_current:
              currentStatements.length,
            odds_history:
              historyStatements.length,
            meta:
              metaStatements.length
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
