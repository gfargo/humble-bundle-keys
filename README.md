# humble-bundle-keys

> Pull every Steam key out of your Humble Bundle account into a single CSV.

[![PyPI version](https://img.shields.io/pypi/v/humble-bundle-keys.svg)](https://pypi.org/project/humble-bundle-keys/)
[![Python versions](https://img.shields.io/pypi/pyversions/humble-bundle-keys.svg)](https://pypi.org/project/humble-bundle-keys/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![CI](https://github.com/gfargo/humble-bundle-keys/actions/workflows/ci.yml/badge.svg)](https://github.com/gfargo/humble-bundle-keys/actions/workflows/ci.yml)

`humble-bundle-keys` walks every page of your [Humble Bundle](https://www.humblebundle.com) Keys & Entitlements list, drives the Humble Choice membership pages on your behalf, captures every revealed key it finds, and writes them all into a single CSV you can sort, search, and bulk-paste into Steam.

It does NOT log into Steam. It stays inside humblebundle.com so the security model is simple.

> **Not affiliated with or endorsed by Humble Bundle.** Humble Bundle and the Humble logo are trademarks of [Tinybuild](https://www.humblebundle.com). This is an independent open-source tool that automates browser actions you could perform yourself.

---

## What it does

1. **Logs you in once** in a real Chromium window (so 2FA emails work normally) and saves the session to `~/.humble-bundle-keys/storage_state.json`. Subsequent runs reuse it silently.
2. **Walks all 195+ orders** via Humble's private JSON API and extracts metadata for every game, key, bundle, deadline, and OS support entry.
3. **Reveals already-allocated keys** by clicking Humble's "Redeem" button on each unrevealed entry — same operation a human would perform.
4. **Claims Humble Choice subscription games** by driving the `/membership/<month>` pages, clicking each unclaimed game card, hitting "GET GAME ON STEAM", waiting for Humble's backend to allocate a key, and extracting it.
5. **Writes everything to `humble-bundle-keys.csv`** with one row per key, structured for sorting/filtering/pasting.

## What it doesn't do

- ❌ Does not log into Steam, GOG, Origin, or any other store. The CSV is for you to bulk-paste yourself.
- ❌ Does not store your Humble password — login happens in a real browser window the first time you run it.
- ❌ Does not make purchases, claim free promos outside the keys page, or modify your account settings.
- ❌ Does not gift games to friends — even though Humble has a "Gift to Friend on Steam" button next to "Get Game on Steam", we deliberately never click it.

---

## Quick start

Requires **Python 3.10+** and **Chromium** (auto-installed via Playwright).

```bash
# Install (using uv, recommended):
uv tool install humble-bundle-keys
playwright install chromium

# Or with pip:
pip install humble-bundle-keys
playwright install chromium
```

```bash
# First run — opens a browser window for login, then walks your library.
humble-bundle-keys

# Recommended first-time flow: read-only preview before anything mutates.
humble-bundle-keys --dry-run -v

# The full thing: extract everything, reveal pre-allocated keys, drive
# Humble Choice membership pages to claim subscription games.
humble-bundle-keys --browser-claim --max-claims 200 -v
```

After the run, your CSV is at `./humble-bundle-keys.csv` and a full DEBUG-level log is at `~/.humble-bundle-keys/runs/run-<timestamp>.log`.

---

## Three modes, when to use which

The tool has three distinct extraction modes that cover different parts of Humble's surface. Most users want all three; you can mix and match.

### 1. Default extract + reveal (`humble-bundle-keys`)

The basic flow. Hits Humble's private JSON API to list all 195+ orders, pulls metadata for every game in your library, and POSTs to `/humbler/redeemkey` for any unrevealed-but-pre-allocated entry to unmask the key. Fast (most of the work is GETs), runs unattended after first login.

Catches: regular bundle keys, legacy Humble Monthly subscription games you'd previously selected but never clicked Redeem on, Humble Choice keys that were already revealed.

### 2. Choice claim via API (`--claim-choice`)

For Humble Choice subscription months where the key hasn't been allocated yet on Humble's side. Drives the documented two-step `POST /humbler/choosecontent` then `POST /humbler/redeemkey` flow that the SPA uses behind "GET GAME ON STEAM". Off by default because it mutates state — you'll get a confirmation prompt unless you pass `-y`.

Catches: current "claim everything" Humble Choice content where the games are listed in your order but `redeemed_key_val` is null.

### 3. Browser-driven Choice claim (`--browser-claim`)

The most thorough mode. Opens each `/membership/<month-slug>` page in a real Chromium window, finds unclaimed game cards, clicks each one, clicks "GET GAME ON STEAM" in the modal, waits for the key to materialize, extracts it. Slower but catches the cases the API can't see (legacy "pick N of M" months where unselected games never appear in your order JSON until claimed).

Catches: Humble Choice subscription games not yet visible in any order, including legacy months with unused choice slots.

```bash
# Combined run: API reveal + browser claim, all in one go.
humble-bundle-keys --browser-claim --max-claims 200 --merge -v
```

`--merge` preserves any keys from a previous CSV that this run might miss (useful if you already have a working CSV from a past run).

---

## Output format

`humble-bundle-keys.csv` — one row per key, these columns:

| column | example |
|---|---|
| `game_title` | `Like a Dragon Gaiden: The Man Who Erased His Name` |
| `platform` | `steam` |
| `key` | `AAAAA-BBBBB-CCCCC` |
| `bundle_name` | `December 2025 Humble Choice` |
| `bundle_date` | `December 2025` |
| `redemption_deadline` | `Must be redeemed by January 6th, 2027.` |
| `redeemed_on_humble` | `true` |
| `os_support` | `Windows` |
| `humble_url` | `https://www.humblebundle.com/downloads?key=…` |

`platform` is normalized to one of: `steam`, `gog`, `origin`, `uplay`, `epic`, `battlenet`, `rockstar`, `xbox`, `microsoft`, `drmfree`, or empty if it can't be determined.

---

## Common flags

| Flag | What it does |
|---|---|
| `--dry-run` | Read-only. Walk everything, don't click Redeem, don't claim Choice games. Use this first. |
| `--no-reveal` | Extract metadata only — don't click Redeem on hidden keys. |
| `--claim-choice` | Run the API-based two-step Choice claim flow. |
| `--browser-claim` | Drive `/membership/<slug>` pages in the browser to claim games. |
| `--membership-only SLUG` | With `--browser-claim`, restrict to one month (e.g. `december-2025`). Useful for testing. |
| `--max-claims N` | Hard cap on Choice claims per run. Default 25. |
| `--claim-delay-s N` | Polite delay between claims. Default 3.0s. |
| `-y` / `--yes` | Skip confirmation prompts (CI/scheduled use). |
| `--merge` | Merge with existing CSV at `--output` instead of overwriting. |
| `-o PATH` / `--output PATH` | Custom CSV path. Default: `./humble-bundle-keys.csv` |
| `--no-cache` / `--cache-ttl-h N` / `--clear-cache` | Control the order-detail JSON cache (default 6h TTL). |
| `--log-file PATH` / `--no-log-file` | Override or disable the auto run-log. |
| `-v` / `-vv` | Bump console verbosity. The on-disk log always captures DEBUG. |
| `--force-login` | Discard the saved session and log in fresh. |

Run `humble-bundle-keys --help` for the full list.

### Subcommands

```bash
humble-bundle-keys diagnose [--membership-page SLUG]  # Capture a sanitized debug bundle for selector bugs.
humble-bundle-keys logout                             # Delete the saved session.
```

---

## Authentication

By default, **persisted browser session**: log in once in the headed Chromium window, the cookies are saved to `~/.humble-bundle-keys/storage_state.json`, and every run after that is silent until the session expires (~1–4 weeks typically).

For CI / scheduled use, you can instead set `HUMBLE_SESSION_COOKIE` to your `_simpleauth_sess` value (from your browser's devtools while logged into humblebundle.com):

```bash
export HUMBLE_SESSION_COOKIE='abc123…'
humble-bundle-keys --no-interactive
```

This takes precedence over the saved storage state.

> The session cookie is bound to your IP and User-Agent. Switching networks (VPN, mobile hotspot) can invalidate it. Run `humble-bundle-keys logout && humble-bundle-keys` to refresh.

---

## What's claimable, what isn't

After a complete run you may see a "Reveals that returned no key" line in the summary. The tool categorizes these so you can tell at a glance which are recoverable:

| Category | What it is | Auto-claimable? |
|---|---|---|
| `choice` | Modern Humble Choice content (`*_choice_steam`, `*_row_choice_steam`, regional variants) | ✅ via `--browser-claim` |
| `monthly` | Legacy Humble Monthly content (`*_monthly_steam`) | ⚠️ Most work via standard reveal. Some are stuck server-side (gifted/expired/refunded) — manual support ticket. |
| `freegame` | Free-game promos (`*_freegame_steam`) | ❌ Different endpoint, not yet supported |
| `keyless` | Epic Games "keyless" delivery (`*_epic_keyless`) | ❌ No key exists — game is added directly to your Epic library |
| `softwarebundle` | Audio/software vendor bundles | ❌ Vendor-specific redemption, varies per vendor |
| `voucher` | Store-credit vouchers (e.g. Synty $10) | ❌ Not a Steam-shaped key |
| `bundle` / `other` | Misc / unrecognized | Investigate via `humble-bundle-keys diagnose` |

See [`docs/WHATS_CLAIMABLE.md`](docs/WHATS_CLAIMABLE.md) for more detail.

---

## Troubleshooting

### "0 keys revealed this run, N errors"

Check the summary's first 5 errors. If they show `<!DOCTYPE html>... no-js ie6 oldie`, that's Cloudflare blocking the request. Re-run with `--no-headless` (since 0.2.5 this is automatic when state will mutate; use `--no-headless` explicitly if you've overridden somewhere).

### "Auth error: /home/keys is still redirecting to login"

Sometimes Humble inserts a region/age-gate page after login. Open `https://www.humblebundle.com/home/keys` in your normal browser, click through whatever it shows, then `humble-bundle-keys logout && humble-bundle-keys`.

### "0 cards found on /membership/<slug>"

Either the slug is wrong (check it loads in your browser) or you're not subscribed to that month (the page renders empty for non-members). The tool walks every order's slug — orders for months you weren't subscribed to will get `0 cards`. Harmless.

### "Key field never populated within timeout"

Humble's claim took longer than 30s. Either re-run (transient) or bump `--claim-delay-s` and try again. If reproducible on a specific game, capture a `humble-bundle-keys diagnose --membership-page <slug>` and open an issue.

### "Reveal calls succeeded but didn't return a key"

Read the categorization in the summary. Most of these are structurally not auto-redeemable (vouchers, keyless, software bundles). The `choice` category is fixable via `--browser-claim`.

### Selector breakage

Humble periodically redesigns their frontend. If selectors stop matching, run `humble-bundle-keys diagnose -v` and attach the resulting `safe-to-share.zip` to a GitHub issue. The bundle is sanitized — keys are replaced with `REDACTED-KEY`, emails with `REDACTED@example.com`, and order gamekeys with `REDACTED-GAMEKEY`.

---

## Architecture

Three modes, one CSV:

```
                          ┌─ ApiScraper ─────────────────────┐
GET /api/v1/user/order ──▶│  list 195 gamekeys               │
                          │  fetch each order's tpkd_dict     │──▶ rows
                          │  POST /humbler/redeemkey for      │
                          │    each unrevealed tpk            │
                          └───────────────────────────────────┘

                          ┌─ ChoiceClaimer ──────────────────┐
                          │  POST /humbler/choosecontent     │
(--claim-choice) ────────▶│  POST /humbler/redeemkey         │──▶ extra rows
                          │  (re-uses ApiScraper.orders)     │
                          └───────────────────────────────────┘

                          ┌─ BrowserChoiceClaimer ───────────┐
                          │  goto /membership/<slug>          │
(--browser-claim) ───────▶│  click each unclaimed card        │──▶ extra rows
                          │  click "Get Game on Steam"        │
                          │  wait for keyfield .redeemed      │
                          │  extract XXXXX-XXXXX-XXXXX        │
                          └───────────────────────────────────┘
                                          │
                                          ▼
                          merge_with_existing → write_csv
```

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the long version, and [`docs/CHOICE_CLAIM_SPEC.md`](docs/CHOICE_CLAIM_SPEC.md) for how the Choice claim flow was reverse-engineered.

---

## Disclaimer

This tool automates browser actions you could perform yourself. It is **not affiliated with or endorsed by Humble Bundle**. Automated access may be against Humble's Terms of Service — use at your own risk. The polite delay between actions exists to keep traffic patterns reasonable; please don't lower it below something a human could plausibly produce.

The tool will never:

- Redeem keys outside humblebundle.com (no Steam, no GOG, etc.)
- Make purchases
- Modify your account settings
- Submit support tickets or contact other users
- Click "Gift to Friend on Steam" — gifts are irrevocable

If you'd rather not have keys auto-claimed, run with `--no-reveal --dry-run`.

---

## Contributing

Issues and PRs welcome. The most fragile part of this tool is the DOM selectors and undocumented API shapes — when those break, a captured diagnose bundle is the fastest path to a fix.

```bash
git clone https://github.com/gfargo/humble-bundle-keys.git
cd humble-bundle-keys
uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"
playwright install chromium

# Run tests
pytest
ruff check humble_bundle_keys tests
```

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for more, and [`SECURITY.md`](SECURITY.md) for our reporting policy on anything sensitive.

---

## License

[MIT](LICENSE) — see file.
