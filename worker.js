function authorized(request, env) {
  const expected = String(env.SYNC_TOKEN || "").trim();

  const headerToken = String(
    request.headers.get("x-sync-token") || ""
  ).trim();

  const auth = String(
    request.headers.get("authorization") || ""
  );

  const bearerToken = auth.startsWith("Bearer ")
    ? auth.slice(7).trim()
    : "";

  return (
    expected.length > 0 &&
    (
      headerToken === expected ||
      bearerToken === expected
    )
  );
}
