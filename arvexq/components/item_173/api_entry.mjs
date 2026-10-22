// Same handler and bindings; no new URL, SQL or acquisition.
export function fetchExisting(worker, request, env, ctx) {
  return worker.fetch(request, env, ctx);
}
