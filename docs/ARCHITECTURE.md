# Architecture

`humble-bundle-keys` is a CLI tool that extracts every game key out of a user's Humble Bundle account into a CSV. It does this by combining three orthogonal mechanisms — pick whichever matches what you're trying to claim. They share auth, share the CSV output, and can run in the same invocation.

This doc explains how the pieces fit together and why the design ended up the way it did.

---

## The three modes

```
                        ┌─ ApiScraper ─────────────────────┐
GET /api/v1/user/order ─┤  list 195 gamekeys               │
                        │  fetch each order's tpkd_dict     │── rows ──┐
(default)               │  POST /humbler/redeemkey for      │          │
                        │    each unrevealed tpk            │          │
                        └───────────────────────────────────┘          │
                                                                       │
                        ┌─ ChoiceClaimer ──────────────────┐           │
(--claim-choice)        │  POST /humbler/choosecontent     │           │
                        │  POST /humbler/redeemkey         │── rows ───┤
                        │  (re-uses ApiScraper.orders)     │           │
                        └───────────────────────────────────┘          │
                                                                       │
                        ┌─ BrowserChoiceClaimer ───────────┐           │
                        │  goto /membership/<slug>          │           │
(--browser-claim)       │  click each unclaimed card        │           │
                        │  click "Get Game on Steam"        │── rows ───┤
                        │  wait for keyfield .redeemed      │           │
                        │  extract XXXXX-XXXXX-XXXXX        │           │
                        └───────────────────────────────────┘          │
                                                                       ▼
                                                  merge_with_existing → write_csv
```

### Mode 1: `ApiScraper` (default, always runs)

Lives in `humble_bundle_keys/api.py`. Hits Humble's private JSON API:

```
GET  /api/v1/user/order              → list of 195 gamekeys
GET  /api/v1/order/<gamekey>?all_tpkds=true → full tpkd_dict per order
POST /humbler/redeemkey              → reveal a single key
```

Each `tpkd_dict.all_tpks[]` entry is one game. Pre-allocated keys live in `redeemed_key_val`; unrevealed entries have `redeemed_key_val: null` and require a POST to `/humbler/redeemkey` to unmask. This handles ~95% of a typical library.

### Mode 2: `ChoiceClaimer` (`--claim-choice`)

Lives in `humble_bundle_keys/choice.py`. For Humble Choice subscription content where the key hasn't been allocated yet on Humble's side, the SPA does a two-step POST sequence:

```
POST /humbler/choosecontent  (registers the user's choice)
POST /humbler/redeemkey      (reveals the now-allocated key)
```

Re-uses the orders fetched by `ApiScraper` (no second list-walk). Default off because it mutates state — `--yes` skips the confirmation prompt.

### Mode 3: `BrowserChoiceClaimer` (`--browser-claim`)

Lives in `humble_bundle_keys/browser_choice.py`. The fallback for cases where the API path can't even *see* the games — legacy "pick N of M" Choice months where unselected games only exist in the membership page's rendered DOM. Drives Chromium directly:

```
goto /membership/<slug>
for each .content-choice:not(.claimed):
    click .choice-content.js-open-choice-modal
    wait for .humblemodal-modal--open
    click .js-keyfield.keyfield.enabled:not(.redeemed):not(.expired)
    poll for .js-keyfield.redeemed .keyfield-value
    extract XXXXX-XXXXX-XXXXX
    close modal
```

Slowest of the three (5–15 seconds per claim because of Humble's backend allocation latency), but catches everything the others miss.

---

## Shared concerns

### Auth

All three modes share a single `BrowserContext` produced by `humble_bundle_keys/auth.py`. Two strategies:

1. **Persisted session** (default) — first run opens a real Chromium window, user logs in by hand, the cookies are saved to `~/.humble-bundle-keys/storage_state.json`. Subsequent runs reuse silently until the session expires.
2. **`HUMBLE_SESSION_COOKIE` env var** (CI / scheduled use) — the user pastes their `_simpleauth_sess` cookie directly. Takes precedence over storage state.

### Why headed mode is forced for state-changing runs

Cloudflare sits in front of `humblebundle.com` and fingerprints HTTP/2 + TLS handshakes. Playwright's bare `APIRequestContext` (which we'd otherwise use for clean POSTs) gets flagged as bot traffic and 403'd on `/humbler/*` endpoints. **GETs slip through** — read-only is fine — but state-changing POSTs need to come from a real Chrome.

So we route all POSTs through `page.evaluate("fetch(...)")` inside the actual headed browser. Same TLS handshake as a real user, same cookies, same JA3/JA4. Cloudflare is happy.

When the user passes `--reveal` / `--claim-choice` / `--browser-claim` (any state-changing flag) without `--dry-run`, the CLI auto-flips `--no-headless` with a notice. Headless Chromium *also* gets flagged regardless of the fetch trick.

See `humble_bundle_keys/_browser_fetch.py` for the implementation.

### Order cache

`humble_bundle_keys/_orders_cache.py` — per-gamekey JSON cache at `~/.humble-bundle-keys/orders-cache/<gamekey>.json` with a 6-hour TTL by default. Cuts a warm 195-order run from ~2 minutes to ~10 seconds. Auto-invalidates when a successful reveal mutates an order. Override with `--cache-ttl-h N` or bypass with `--no-cache`.

### CSV merge identity

`merge_with_existing` in `humble_bundle_keys/exporter.py` uses `(humble_url, game_title, platform)` as the row identity — never `bundle_name`, because earlier versions of the tool extracted `bundle_name` from the wrong API field, leaving it blank in old CSVs. Using `humble_url` (which carries the stable order gamekey) means an old blank-bundle-name row collapses cleanly with a freshly-extracted populated-bundle-name row.

### Diagnose bundle (sanitized debug capture)

`humble_bundle_keys/diagnose.py` — `humble-bundle-keys diagnose` opens a headed browser, navigates `/home/keys` and optionally `/membership/<slug>`, captures all XHR responses + page HTML + screenshots, then runs everything through a sanitizer that replaces:

- Steam-shaped keys → `REDACTED-KEY`
- Email addresses → `REDACTED@example.com`
- `?gamekey=` URL parameters → `REDACTED-GAMEKEY`
- A fixed list of sensitive HTTP headers (Cookie, Set-Cookie, Authorization, CSRF-Prevention-Token, X-CSRF-Token, X-CSRFToken, X-XSRF-Token) → stripped entirely

Outputs a `safe-to-share.zip` users can attach to GitHub issues. The 14 sanitizer tests in `tests/test_diagnose_sanitiser.py` cover every category we know about; `raw/` is never sanitized, only the `safe-to-share/` copy.

---

## Why three separate modes instead of one unified scraper

Tried unifying. Doesn't work cleanly because the three flows have genuinely different cost / risk / coverage profiles:

| | API reveal | Choice claim API | Browser claim |
|---|---|---|---|
| Speed | Fast (POST per game, ~1s each) | Fast (2 POSTs per game) | Slow (5–15s per game, full DOM) |
| Visibility | Background | Background | Visible browser window |
| Coverage | ~95% of typical library | Modern Choice months only | Everything API can't see |
| Failure mode | Silent no-key (we now categorize) | Server-side error (Road 96 case) | Modal/timing issues |
| Side effects | Reveals key + marks claimed on Humble | Same | Same + visible UI changes |

The user can mix: a typical full-coverage run is `humble-bundle-keys --browser-claim --merge -v`, which runs all three sequentially.

---

## Module map

```
humble_bundle_keys/
├── __init__.py           Version
├── __main__.py           python -m humble_bundle_keys
├── cli.py                argparse + subcommand dispatch + summary table
├── auth.py               Persisted-session login, env-var fallback
├── api.py                ApiScraper — JSON API path for everything readable
├── choice.py             ChoiceClaimer — two-step Choice claim via API
├── browser_choice.py     BrowserChoiceClaimer — DOM-driven Choice claim
├── scraper.py            DOM scraper (legacy, mostly replaced by ApiScraper)
├── diagnose.py           Sanitized debug-capture subcommand
├── exporter.py           CSV writer + merge-with-existing
├── models.py             GameKey, ExtractStats, CSV_HEADERS
├── _browser_fetch.py     post_form_in_browser() — Cloudflare-friendly POSTs
└── _orders_cache.py      Per-gamekey JSON cache
```

Tests mirror the module structure 1:1 in `tests/`.
