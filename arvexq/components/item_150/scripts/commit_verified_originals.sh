#!/usr/bin/env bash
set -e -o pipefail
git config user.name 'github-actions[bot]'
git config user.email '41898282+github-actions[bot]@users.noreply.github.com'
git add arvexq/ui/static/saved-snapshots
if git diff --cached --quiet; then exit 0; fi
git commit -m "fix: restore hash-verified saved race originals for $RECOVERY_DATE"
git pull --rebase origin main
git push origin main
