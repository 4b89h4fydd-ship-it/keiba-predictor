#!/usr/bin/env bash
set -e -o pipefail
python scripts/arvexq_publish_saved_snapshots.py --root .arvexq-data --date "$RECOVERY_DATE"
test -s "arvexq/ui/static/saved-snapshots/$RECOVERY_DATE.json"
python build_static.py
