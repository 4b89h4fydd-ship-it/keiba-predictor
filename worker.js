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
