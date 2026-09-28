export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    if (url.pathname === "/api/health") {
      return Response.json({
        ok: true,
        service: "KRAIZ API",
        version: "cloudflare-bootstrap-v1"
      });
    }

    if (url.pathname === "/api/db-check") {
      const result = await env.DB.prepare(`
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
        ORDER BY name
      `).all();

      return Response.json({
        ok: true,
        tables: result.results
      });
    }

    return Response.json({
      ok: true,
      service: "KRAIZ API",
      message: "ready"
    });
  }
};
