#!/usr/bin/env bash
# Fail closed. The official B/K feed must never be copied into a public repo
# or into a public Cloudflare Worker assets route.
set -euo pipefail
DAY="${1:-$(TZ=Asia/Tokyo date +%F)}"
BASE="${ARVEXQ_BOAT_PRIVATE_HOST:-https://kraizweb1.4b89h4fydd.workers.dev}"
: "${CLOUDFLARE_ACCESS_CLIENT_ID:?Private Cloudflare Access service token ID required}"
: "${CLOUDFLARE_ACCESS_CLIENT_SECRET:?Private Cloudflare Access service token secret required}"
: "${CLOUDFLARE_API_TOKEN:?Cloudflare deployment credentials required}"

check_private(){
  local path="$1" headers status location
  headers="$(mktemp)"
  status="$(curl -sS --max-time 15 -D "$headers" -o /dev/null -w '%{http_code}' "$BASE$path?personal-probe=$GITHUB_RUN_ID" || true)"
  location="$(grep -i '^location:' "$headers" | tail -1 | tr -d '\r' || true)"
  rm -f "$headers"
  if [[ "$status" == "401" || "$status" == "403" ]]; then
    echo "PRIVATE_ACCESS_DENIED_UNAUTH path=$path status=$status"
  elif [[ "$status" =~ ^30[12378]$ ]] && [[ "$location" == *cloudflareaccess.com* || "$location" == */cdn-cgi/access/* ]]; then
    echo "PRIVATE_ACCESS_LOGIN_UNAUTH path=$path status=$status"
  else
    echo "::error::UNPROTECTED_BOAT_HOST path=$path status=$status"
    exit 1
  fi
}
# Access must protect the host, not just /kyotei/. Anonymous access to
# /sports/boat-data remains redistribution regardless of the user interface.
check_private "/"
check_private "/kyotei/"
check_private "/sports/boat-data/$DAY.json"
if [[ "${2:-}" == "--verify-only" ]]; then
  localfile="dist/sports/boat-data/$DAY.json"
  test -s "$localfile"
  status="$(curl -sS --max-time 25 \
     -H "CF-Access-Client-Id: $CLOUDFLARE_ACCESS_CLIENT_ID" \
     -H "CF-Access-Client-Secret: $CLOUDFLARE_ACCESS_CLIENT_SECRET" \
     -H 'Cache-Control: no-cache' \
     "$BASE/sports/boat-data/$DAY.json?verify=$GITHUB_RUN_ID" \
     -o /tmp/boatrace-private-verification.json -w '%{http_code}')"
  test "$status" = "200"
  python - "$localfile" /tmp/boatrace-private-verification.json <<'PY'
import hashlib,sys,json
a,b=(open(p,'rb').read() for p in sys.argv[1:])
if hashlib.sha256(a).digest()!=hashlib.sha256(b).digest():
    raise SystemExit("PRIVATE_BOAT_PRODUCTION_HASH_MISMATCH")
j=json.loads(b)
if not j.get("personalOnly") or not j.get("verified") or not j.get("races"):
    raise SystemExit("PRIVATE_BOAT_PRODUCTION_DATA_INVALID")
print("PRIVATE_BOAT_PRODUCTION_VERIFIED",j['date'],"races",len(j['races']),
      "confirmed",sum(x.get('result',{}).get('status')=='confirmed' for x in j['races']))
PY
  exit 0
fi
export ARVEXQ_BOAT_PRIVATE_ACCESS_VERIFIED=1
python scripts/arvexq_boat_official.py --date "$DAY" --publish \
  --cache-dir "${RUNNER_TEMP:-/tmp}/arvexq-official-bk" \
  --output "${RUNNER_TEMP:-/tmp}/arvexq-official-day"
echo "PRIVATE_BOAT_IMPORT_READY day=$DAY"
