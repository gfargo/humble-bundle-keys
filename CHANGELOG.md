# Changelog

All notable changes to `humble-bundle-keys` will be documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Validated

- 0.4.0 exercised end-to-end against a large multi-year account (200+ orders): default API reveal path returned a CSV in a single pass with a >99% success rate, and the silent-no-key categorizer correctly bucketed every non-Steam-shaped entry (softwarebundle / voucher / keyless / freegame / monthly).

### Known issues (filed against this release)

- Transient Cloudflare 403s on a single reveal POST (~0.5% rate observed). Tracked as a bug — fix is retry-with-backoff in `_browser_fetch`.
- Cache hit/miss summary line prints counts that don't sum to the order count. Cosmetic, fix planned.
- `softwarebundle`, `voucher`, `keyless`, and `freegame` keytypes still trigger a wasted reveal POST before being categorized. Tracked as an enhancement to pre-skip them.
- Choice re-run hint should print a copy-pasteable `--claim-choice --membership-only <slug>` invocation.

## [0.4.0] — Public release

### Changed
- **Renamed package and CLI from `humble-keys` to `humble-bundle-keys`** for discoverability. Repo: `github.com/gfargo/humble-bundle-keys`. PyPI: `humble-bundle-keys`. Python module: `humble_bundle_keys`. Trademark-respectful framing: clear "not affiliated with Humble Bundle" disclaimer in README.
- README rewritten end-to-end for 0.4.0 reality — covers all three modes (default reveal / `--claim-choice` / `--browser-claim`), the order cache, run logging, the silent-no-key categorization, and what's structurally claimable vs not.
- Pyproject URLs updated to point at the new repo, plus added `Repository` and `Changelog` URLs.

### Added
- `.gitignore` hardened against accidental leaks: `humble-diagnose/`, `orders-cache/`, `runs/`, `.env*`, `*.log`, debug screenshots, anything `MY_*`. Existing ignores kept (storage_state.json, *.csv, etc.) and migrated to the new `~/.humble-bundle-keys/` directory while preserving legacy `~/.humble-keys/` for in-flight users.
- `CONTRIBUTING.md`, `SECURITY.md`, GitHub issue templates.
- `docs/ARCHITECTURE.md` and `docs/WHATS_CLAIMABLE.md`.

## [0.3.5] — Run log files

### Added
- All runs now auto-write a full DEBUG-level log to `~/.humble-bundle-keys/runs/run-<timestamp>.log` with last-20 retention. `--log-file PATH` overrides; `--no-log-file` disables. Console verbosity (`-v`/`-vv`) is decoupled from on-disk capture.
- Summary now prints the log path so it's discoverable without `-v`.

## [0.3.4] — Browser-claim wait fix + skip expired

### Fixed
- **Wait loop no longer breaks early on the "claimed" banner.** That signal fires ~1s after the click, but Humble's backend takes another 5–15s to write the actual key. We now poll the keyfield until either we get a real `XXXXX-XXXXX-XXXXX` string or hit the timeout — no shortcuts.
- **Pre-click detection of `.expired` keyfields.** Subscription-trial entries (IGN Plus, Boot.dev) have `class="js-keyfield keyfield expired"` and a "This key has expired" placeholder. Clicking them does nothing. We now skip them cleanly instead of burning the full timeout per game.
- Default `key_wait_ms` bumped from 20s to 30s for slow Humble responses on top-tier titles.

## [0.3.3] — Browser-claim DOM selectors

### Fixed
- **Modal selectors now match Humble's actual DOM.** Previous versions assumed a `<button>` for "Get Game on Steam" — the real element is a `<div class="js-keyfield keyfield enabled">` styled as a button. The same `.keyfield-value` div holds both the placeholder ("Get game on Steam") and the post-claim key, with parent `.redeemed` class as the discriminator.
- `_extract_key` now strictly requires `KEY_PATTERN` match and explicitly rejects the placeholder strings — fixes the bug where the button label was being saved as a "key" in the CSV.

## [0.3.2] — Click-target tightening

### Fixed
- Replaced `*:has-text('GET GAME ON STEAM')` with role-restricted selectors (`button.button-v2`, `button`, `a.button-v2`, `a`). The wildcard fallback was matching the modal wrapper itself; clicking it hit the backdrop and closed the modal instead of triggering the claim.
- `_extract_key` no longer falls back to "any short text" when no match is found — fixes the bug where empty modals returned the button label as a "key".

## [0.3.1] — Order cache + browser-claim hardening

### Added
- **Per-order JSON cache** at `~/.humble-bundle-keys/orders-cache/<gamekey>.json` with default 6h TTL. Cuts a warm run from ~2 minutes to ~10 seconds. Auto-invalidates after a successful reveal so the next run picks up new keys. CLI: `--no-cache`, `--cache-ttl-h N`, `--clear-cache`.

### Fixed
- `BrowserChoiceClaimer` post-click wait scoped to the just-opened modal instead of the page. Prevents stale `.keyfield-value` elements from already-claimed cards on the same page from short-circuiting the wait.
- Anchor pages in both `ApiScraper` and `ChoiceClaimer` self-heal if they drift off-origin (auth-refresh redirect etc.).
- Dry-run skips no longer counted as failures in the summary.

## [0.3.0] — Browser-driven Choice claim

### Added
- **`--browser-claim`** — drives the actual `/membership/<slug>` membership pages in Chromium. For each Choice/Monthly month with unclaimed games, finds each card on the page, clicks "GET GAME ON STEAM" in the modal, waits for Humble to allocate the key, extracts it. Catches the cases the API path can't see (legacy "pick N of M" months where unselected games never appear in your order JSON).
- **`--membership-only SLUG`** — restrict `--browser-claim` to one membership page. Useful for testing.
- New module `humble_bundle_keys.browser_choice` with `BrowserChoiceClaimer`, `derive_membership_slug`, plus DOM-selector constants derived from a captured diagnose bundle.

## [0.2.7] — Choice typo + categorization

### Fixed
- Choice keytype regex now matches Humble's real-world `_hoice_` typo (e.g. `road96_europe_hoice_steam` is genuinely missing a `c`).

### Added
- `categorize_keytype()` — labels each silent-no-key tpk as one of `choice` / `monthly` / `freegame` / `keyless` / `softwarebundle` / `voucher` / `bundle` / `other` so the run summary tells users at a glance which holdouts are recoverable vs structurally manual.

## [0.2.6] — Silent-no-key diagnostics

### Added
- Run summary now lists each silent-no-key tpk's title + `tpk.machine_name` + `order.machine_name` (first 10 shown, ellipsis for the rest). Makes it possible to refine pattern detection without a full diagnose run.

## [0.2.5] — Auto-headed for reveals + anchor-page healing + silent-no-key signal

### Fixed
- **Anchor page heals when navigation context is lost.** A run that worked otherwise had one entry fail with `Page.evaluate: Execution context was destroyed, most likely because of a navigation`. Both `ApiScraper._get_anchor_page` and `ChoiceClaimer._get_anchor_page` now check the page's URL each call, re-navigate to humblebundle.com if it's drifted off-origin, and fall back to a fresh page if re-navigation fails.

### Changed
- **`humble-bundle-keys` now auto-flips to `--no-headless` when the run will mutate state** (i.e. `--reveal` and/or `--claim-choice`, when not in `--dry-run`). Verified via 0.2.4: `--headless` produces 0 reveals and 167 Cloudflare 403s; `--no-headless` produces 144 reveals and 2 errors. The fix is structural — Cloudflare's bot management rejects state-changing POSTs from headless Chromium even when the SPA itself works fine. Users who really want headless can pass `--no-reveal --dry-run` together.

### Added
- New stat `keys_silent_no_response` — counts reveal calls that returned 2xx but didn't yield a key. The summary surfaces them with a hint that those are likely Humble Choice subscription games that need the two-step `--claim-choice` flow rather than the direct redeemkey path.

## [0.2.4] — Bypass Cloudflare bot detection on POSTs

### Fixed
- **All `/humbler/redeemkey` and `/humbler/choosecontent` POSTs were being 403'd by Cloudflare.** Cloudflare fingerprints incoming HTTP/2 + TLS handshakes and was flagging Playwright's `APIRequestContext` as bot traffic. We now route POSTs through the actual browser via `page.evaluate("fetch(...)")` — Cloudflare sees a real Chrome request from the same origin with normal cookies, lets it through. GETs continue to use `APIRequestContext` since they don't trigger the challenge. Diagnosed from a 0.2.3 run that returned `<!DOCTYPE html>... <html class="no-js ie6 oldie">` (the Cloudflare challenge template) on every reveal attempt.
- New module `humble_bundle_keys._browser_fetch` with a single helper `post_form_in_browser(page, url, body, ...)` shared between `ApiScraper` and `ChoiceClaimer`.
- Both scrapers now lazily open an "anchor page" navigated to humblebundle.com on first POST, and close it when scraping ends.

### Added
- 6 tests in `tests/test_browser_fetch.py` for the JS payload shape, header construction, and 4xx response handling.

## [0.2.3] — Surface reveal errors

### Improved
- Reveal errors are now logged at WARNING level (so `-v` exposes them) and the run summary prints the first 5 errors verbatim. Previously the count was visible but the messages required a re-run.

## [0.2.2] — Reveal headers + stable merge identity

### Fixed
- **`api.py::_reveal` now sends the same headers Humble's frontend uses** for `/humbler/redeemkey` calls: `X-Requested-With: XMLHttpRequest`, `Accept: application/json, text/javascript, */*; q=0.01`, and `Referer: https://www.humblebundle.com/home/keys`. Without `X-Requested-With`, Humble's backend appears to reject the call (acts as a soft anti-CSRF check). Fixes 0.2.1's "0 keys revealed, 167 errors" symptom — we were now making the calls (post-keyindex-fix) but they were being rejected.
- **`exporter.merge_with_existing` now uses a stable identity** (`humble_url` + `game_title` + `platform`) instead of `(game_title, bundle_name, platform)`. Earlier versions extracted `bundle_name` from the wrong API field, leaving it blank in older CSVs; merging an old CSV with a freshly-extracted run was producing duplicate rows when the bundle_name went from "" to (e.g.) "August 2019 Humble Monthly". Existing rows now collapse correctly even when the bundle_name was blank.

### Improved
- 4XX responses from `/humbler/redeemkey` now include up to 200 chars of the response body in the error message — surfaces server-provided rejection reasons in the run summary.

## [0.2.1] — Critical reveal fix

### Fixed
- **`humble_bundle_keys.api.ApiScraper._reveal` now uses the correct field name** for `keyindex` on order tpks. Humble's API uses `keyindex` (one word); we were reading `key_index` (with underscore), which always returned `None`, causing the precondition to silently bail on every single unclaimed tpk. Verified against captured production data: the old code would have called `/humbler/redeemkey` for 0 of 167 unclaimed tpks; the new code will call it for all 167. **This is why prior runs reported "0 keys revealed" despite many unclaimed games.**
- `humble_bundle_keys.choice.ChoiceClaimer.claim_one` had the same bug; also fixed.
- `humble_bundle_keys.api._extract_tpk` now reads `bundle_name` from the actual location (`order.product.machine_name` / `order.product.human_name`) instead of the root level, where those fields don't exist. Falls back to root for tolerance.
- `humble_bundle_keys.choice.looks_like_choice_order` now reads `product.category=="subscriptioncontent"` and `product.machine_name` (the real shape) instead of the root, and explicitly rejects legacy Humble Monthly orders (those use Flow A directly, not the two-step claim).

### Changed
- Broadened the Choice keytype regex to match all observed real-world patterns: `_choice_steam` (no modifier), `_row_choice_steam`, `_naeu_choice_steam` (regional), `_choice_epic_keyless` (multi-word platform). Previously only matched `_row_choice_<word>`.

## [0.2.0] — Humble Choice claim support

### Added
- **`--claim-choice` flag** — drives the two-step `POST /humbler/choosecontent` + `POST /humbler/redeemkey` flow that Humble's frontend uses behind "GET GAME ON STEAM" on `/membership/<month>` pages. Off by default. Includes `--max-claims` (default 25), `--claim-delay-s` (default 3.0), and a `--yes` confirmation skip for non-interactive use. See `docs/CHOICE_CLAIM_SPEC.md` for the discovered API contract.
- New module `humble_bundle_keys.choice` with the `ChoiceClaimer` class plus pure helpers (`is_choice_keytype`, `short_id_for_keytype`, `looks_like_choice_order`, `unclaimed_choice_tpks`, `build_choosecontent_body`, `build_redeemkey_body`, `extract_revealed_key`).
- `humble-bundle-keys diagnose --membership-page <slug>` — captures sanitised diagnostic artifacts of the Choice page interaction, with PII / keys / session tokens redacted. Reuses the existing browser window and supports an Enter-to-stop completion signal in the terminal.
- Diagnose XHR capture broadened to all of `humblebundle.com` (excluding static assets), and now records request method, headers, and body alongside the response. Sensitive headers (Cookie, Set-Cookie, Authorization, CSRF-Prevention-Token, X-CSRF-Token, X-XSRF-Token) are stripped before write.
- `tests/fixtures/choice_claim/` — sanitised live captures of the four wire calls behind one "GET GAME ON STEAM" click, used as test fixtures.
- 17 new tests (8 redaction + 9 Choice-flow) on top of the existing 39.

### Changed
- `ApiScraper` now exposes a `.orders` list of fetched order JSON blobs so the Choice claim phase can reuse them without re-fetching.
- `_run_scraper` returns a 3-tuple `(rows, stats, api_or_none)` so callers can chain into the Choice claim phase.

### Fixed
- `humble-bundle-keys diagnose --membership-page` previously opened a second browser window and could miss a closed-tab event. Now reuses the existing page (one window only) and adds an Enter-to-stop signal as the primary completion path.

## [0.1.0] — initial release

### Added
- Initial release.
- Persisted-session auth: first run opens a real browser for login, subsequent runs are headless.
- `HUMBLE_SESSION_COOKIE` env-var auth as a CI-friendly alternative.
- DOM scraper with multiple selector fallbacks for resilience.
- JSON API scraper using Humble's private `/api/v1/order` endpoints.
- `--scraper {auto,api,dom}` flag — `auto` tries the API first and falls back to DOM if the response shape is unrecognised.
- `humble-bundle-keys diagnose` subcommand: read-only capture run that produces a sanitised `safe-to-share.zip` for debugging selector or API drift, with PII stripped (keys → `REDACTED-KEY`, emails → `REDACTED@example.com`, gamekey URL params → `REDACTED-GAMEKEY`).
- `humble-bundle-keys logout` subcommand: deletes the saved session.
- `--merge` mode preserves keys revealed in previous runs even if a fresh extract misses them.
- Rich CSV output: `game_title, platform, key, bundle_name, bundle_date, redemption_deadline, redeemed_on_humble, os_support, humble_url`.
- 39 unit tests covering parsers, exporter, API parsing, and the diagnose sanitiser.
- CI workflow on Python 3.10/3.11/3.12; release workflow with PyPI trusted publishing.
