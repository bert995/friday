# Friday landing page

The marketing/landing site for 周五 lives in [`site/`](site/) — a single static
`index.html` + the cat sprites in `site/assets/cat/`. No build step.

## Preview locally

```bash
cd site && python3 -m http.server 8765
# open http://127.0.0.1:8765/
```

## Deploy to friday.bochen.uk (Cloudflare Pages)

bochen.uk is a Cloudflare zone (same setup as `assets.bochen.uk`). The site is a
Cloudflare Pages project named `friday-site`.

```bash
./deploy-site.sh          # creates the project (first time) + uploads site/
```

### Custom domain: friday.bochen.uk

The domain is **already attached** to the `friday-site` project (added via the
Cloudflare API, 2026-05-27 — it shows as `pending`). It only needs its DNS
record, which couldn't be created from here because the cached wrangler OAuth
token has `zone:read` but not `dns_records:write`.

Add this one record in the Cloudflare dashboard (zone **bochen.uk** → DNS →
Add record), then it goes active + provisions the cert automatically:

| Type | Name | Target | Proxy |
|------|--------|----------------------|-----------|
| CNAME | `friday` | `friday-site.pages.dev` | Proxied (🟠 on) |

After that, every `./deploy-site.sh` updates the live site.

## What the site claims (keep it true)

The page describes the *real* app, not a generic template:

- Stack: **Python + pywebview**, packaged via `./build.sh` → `Friday.app`.
- Brain: **100% local** via oMLX + `Qwen3.5-4B-4bit` — no cloud API, no key, no cost.
- Platform: **macOS, Apple Silicon only** (MLX is Apple-Silicon-bound).
- The "克隆" buttons point at `https://github.com/bert995/friday`.

If you change a feature in the app, update the matching section in `site/index.html`.
