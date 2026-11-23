#!/usr/bin/env bash
# Build static API packs directly from a lane's local payload and commit
# them to main (GitHub-only migration, block A).
#
# Usage:
#   bash scripts/arvexq_static_api_lane_publish.sh <payload.json> [full|merge]
#
#   full  -- the payload is a complete day (prefetch-payload.json);
#            the packs for its date are regenerated from it alone.
#   merge -- the payload is a delta (live-payload.json,
#            rewrite-publish-payload-<date>.json); it is overlaid on the
#            packs already committed for the same date.
#
# This is a parallel, fail-soft lane: it never fails the calling job
# (always exits 0) and never touches the D1 sync path.  It follows the
# same publish pattern as the racecard / morning-picks static steps:
# rebuild on top of the latest origin/main, commit only the pack tree,
# push with retries, then dispatch the web deploy explicitly (GITHUB_TOKEN
# pushes do not trigger push workflows).
set -u

PAYLOAD="${1:-}"
MODE="${2:-full}"
if [ -z "$PAYLOAD" ] || [ ! -s "$PAYLOAD" ]; then
  echo "STATIC_API_LANE_SKIP no payload: ${PAYLOAD:-<empty>}"
  exit 0
fi
cp "$PAYLOAD" /tmp/arvexq-static-api-payload.json

git config user.name "ARVEXQ Static API Bot"
git config user.email "41898282+github-actions[bot]@users.noreply.github.com"

BUILD_ARGS="--input /tmp/arvexq-static-api-payload.json --out-dir arvexq/ui/static/api-static --prune-days 14"
if [ "$MODE" = "merge" ]; then
  BUILD_ARGS="$BUILD_ARGS --merge-existing"
fi

for attempt in 1 2 3 4; do
  if ! git fetch origin main; then
    echo "::warning::STATIC_API_LANE fetch failed (attempt $attempt)"
    continue
  fi
  if ! git checkout -B publish-static-api origin/main; then
    echo "::warning::STATIC_API_LANE checkout failed (attempt $attempt)"
    continue
  fi
  # shellcheck disable=SC2086
  if ! python scripts/arvexq_static_api_build.py $BUILD_ARGS; then
    echo "::warning::STATIC_API_LANE build failed; keeping last packs"
    exit 0
  fi
  git add arvexq/ui/static/api-static
  if git diff --cached --quiet; then
    echo "STATIC_API_LANE_UNCHANGED"
    exit 0
  fi
  git commit -m "data: static api packs (lane direct $MODE)"
  if git push origin HEAD:main; then
    gh workflow run arvexq-web-deploy.yml --ref main || \
      echo "::warning::Static API committed; Web Deploy dispatch not accepted"
    echo "STATIC_API_LANE_PUBLISHED mode=$MODE"
    exit 0
  fi
  echo "::warning::STATIC_API_LANE push race (attempt $attempt); retrying on latest main"
done
echo "::warning::STATIC_API_LANE_PUBLISH_DEFERRED packs could not be pushed after retries"
exit 0
