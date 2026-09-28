function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: {
      "content-type": "application/json; charset=utf-8",
      "cache-control": "no-store",
      "access-control-allow-origin": "*"
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

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const path = url.pathname;

    try {
      // Health
      if (path === "/api/health") {
        return json({
          ok: true,
          service: "KRAIZ API",
          version: "cloudflare-api-v2"
        });
      }

      // DB check
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

      // Race list
      // /api/races?date=2026-09-28
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

      // Race detail
      // /api/race/<race_id>
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

      // Current odds
      // /api/odds/<race_id>
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

      return json({
        ok: true,
        service: "KRAIZ API",
        endpoints: [
          "/api/health",
          "/api/db-check",
          "/api/races?date=YYYY-MM-DD",
          "/api/race/<race_id>",
          "/api/odds/<race_id>"
        ]
      });

    } catch (err) {
      return json({
        ok: false,
        error: String(err?.message || err)
      }, 500);
    }
  }
};
