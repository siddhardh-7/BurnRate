#!/usr/bin/env bash
# Overwrites dashboards/*.json with the live, working dashboards pulled from
# this Mac's self-hosted SigNoz via GET /api/v1/dashboards/{id}.
#
# Why this exists: the checked-in dashboards/*.json predate the working
# format (see memory/decisions.md — "Dashboards managed via API, not UI
# import"). They were built by hand in an ad-hoc `layout`-only shape and
# import as empty. The real ones, pushed via PUT, are the source of truth —
# this script pulls them back down so the repo matches what's deployed.
#
# Must be run from a machine that can reach the local SigNoz instance
# (localhost:8080) — i.e. your Mac, not a sandboxed/remote shell.
set -euo pipefail
cd "$(dirname "$0")/.."

set -a
source .env
set +a

: "${SIGNOZ_API_KEY:?SIGNOZ_API_KEY not set in .env}"
SIGNOZ_API_URL="${SIGNOZ_API_URL:-http://localhost:8080}"

declare -A DASHBOARDS=(
  [dashboards/burn-rate-live.json]="019f4162-70e4-7193-8773-ab93ca8efcfb"
  [dashboards/cost-by-agent.json]="019f4162-cf1b-79a0-8225-c1cae4514bc1"
  [dashboards/model-efficiency.json]="019f4163-23fb-7988-b600-d1eb99fcb2d2"
)

for file in "${!DASHBOARDS[@]}"; do
  id="${DASHBOARDS[$file]}"
  echo "Fetching $id -> $file"
  curl -sf "$SIGNOZ_API_URL/api/v1/dashboards/$id" \
    -H "SIGNOZ-API-KEY: $SIGNOZ_API_KEY" \
  | python3 -c '
import json, sys
node = json.load(sys.stdin)
# The API wraps the dashboard in nested {"data": ...} envelopes depending on
# version; unwrap until we find the actual widgets+layout object, or give up
# after a few hops so the raw response is visible for debugging instead of
# silently writing garbage.
for _ in range(4):
    if isinstance(node, dict) and "widgets" in node and "layout" in node:
        break
    if isinstance(node, dict) and "data" in node:
        node = node["data"]
    else:
        break
json.dump(node, sys.stdout, indent=2)
print()
' > "$file"
  if grep -q '"widgets"' "$file" && grep -q '"layout"' "$file"; then
    echo "  ok: widgets + layout present"
  else
    echo "  WARNING: $file does not look like a widgets+layout dashboard — inspect it before committing" >&2
  fi
done

echo
echo "Done. Review with: git diff --stat dashboards/"
