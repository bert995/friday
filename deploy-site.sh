#!/bin/bash
# Deploy the Friday landing page (site/) to Cloudflare Pages.
#
# Project:  friday-site   →  served at https://friday.bochen.uk
#           (after the custom domain is attached once in the CF dashboard).
#
# Prereqs: a Cloudflare account + `wrangler login` done once. If wrangler isn't
# installed globally this script falls back to `npx wrangler`.
set -euo pipefail
cd "$(dirname "$0")"

PROJECT=friday-site
WRANGLER="wrangler"
command -v wrangler >/dev/null 2>&1 || WRANGLER="npx --yes wrangler"

echo "→ Ensuring Pages project '$PROJECT' exists ..."
$WRANGLER pages project create "$PROJECT" --production-branch=main 2>/dev/null || true

echo "→ Deploying site/ ..."
$WRANGLER pages deploy site --project-name="$PROJECT" --branch=main --commit-dirty=true

cat <<'EOF'

✅ Uploaded. You now have a https://friday-site.pages.dev URL.

One-time, in the Cloudflare dashboard:
  Pages → friday-site → Custom domains → Set up a custom domain → friday.bochen.uk
(bochen.uk is already a Cloudflare zone, same as assets.bochen.uk, so it just
adds the CNAME for you.)
EOF
