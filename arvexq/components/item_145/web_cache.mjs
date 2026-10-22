// Delegate once to the same existing cache/live-odds handler.
export function fetchExisting(worker, request, env, ctx) {
  return worker.fetch(request, env, ctx);
}
