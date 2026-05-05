# Humble Choice "Get Game on Steam" claim flow — spec

**Status:** API contract captured (2026-05-04). Implementation in progress.
**Owner:** @gfargo
**Last updated:** 2026-05-04

This is a living document. Append new findings as bullet points under the
relevant section rather than rewriting; we want the trail of what we knew
when, so future-you (or another contributor) can reconstruct the reasoning.

---

## TL;DR

Humble has **two distinct "claim a key" flows**, and the current `humble-bundle-keys`
codebase only handles one of them.

| Flow | Where it lives | Endpoint we use | Status |
|---|---|---|---|
| **A. Standard Redeem** | `/home/keys` — green "Redeem" button next to a row | `POST /humbler/redeemkey` (form-encoded with `keytype`, `key`, `keyindex`) | ✅ Implemented in `humble_bundle_keys/api.py::_reveal` |
| **B. Choice "Get Game on Steam"** | `/membership/<month-slug>` — card grid → modal → blue "GET GAME ON STEAM" button → 3–10 s async → modal updates with key | **UNKNOWN** | ❌ Not implemented; subject of this spec |

The first dry run on a real account (Griffen, 2026-05-04) returned **589
rows from 195 orders, 422 already-revealed keys, 0 newly revealed**. The
167-key gap (589 − 422 = 167) is presumed to be Choice subscription content
sitting in Flow B and not reachable via Flow A.

The desired behaviour from `humble-bundle-keys` is the same as for Flow A: trigger
the claim so the key materialises on Humble's side, then capture it into
the CSV. We are explicitly **not** going to drive the subsequent "REDEEM"
button that activates the key on Steam — that's a separate, larger problem.

---

## What we observed (from screenshots, 2026-05-04)

### Entry points

* On `/home/keys`, a Humble Choice month appears as a single bundle row
  ("MARCH 2026 HUMBLE CHOICE") with a blue **"GET MY GAMES"** button — not
  the usual "Redeem" button. Clicking that button **navigates** to
  `humblebundle.com/membership/<month-slug>` (e.g. `/membership/march-2026`).
* The `/membership/<month-slug>` page shows a card grid titled
  "MARCH 2026 GAMES" with one card per included game. Each card shows the
  cover art, title, and a small Steam icon at the bottom.
* There is also a "SELECT GAMES" button at the top of the grid for older /
  legacy Choice tiers where the user chose a subset; for current months
  every game is included automatically.

### Modal — pre-claim state

Clicking a card opens a modal with:

* Title + genre + publisher + retail price (e.g. "$39.99")
* Cover art on the left
* Trailer embed on the right
* Two buttons stacked under the cover art:
  * **GET GAME ON STEAM** (primary, blue) ← this is what we automate
  * **GIFT TO FRIEND ON STEAM** (secondary) ← we deliberately do NOT touch this
* "Must be redeemed by `<date>` Pacific Time." (Choice deadlines tend to be
  shorter than ad-hoc bundle deadlines — months vs. years)
* A "REJOIN" CTA (unrelated, points back to membership management)
* Platform: STEAM • Operating systems: Windows
* "RATINGS" — Steam review score
* X / close button

### Modal — post-claim state

After clicking "GET GAME ON STEAM", a 3–10 second async operation runs.
When it completes the same modal updates in place:

* An orange "**CLAIMED**" banner pinned to the top of the modal
* The card art gets a "CLAIMED" pill in the top-left corner
* The button stack is replaced by:
  * Section header **"HERE'S YOUR KEY"**
  * A monospace pill with the actual Steam key (example seen:
    `AAAAA-BBBBB-CCCCC`)
  * A **REDEEM** button — which we believe opens Steam's URL handler /
    deep-link to redeem on Steam itself (this is the bit we *don't* automate)

### Behavioural notes

* The "REDEEM" button at the bottom of the post-claim state is **NOT** the
  same affordance as the green "Redeem" button on `/home/keys`. The former
  hands the key off to Steam for activation; the latter is what triggers
  Flow A on Humble's own backend. They share a name but do different things.
* After a card is claimed on `/membership/<slug>`, the corresponding entry
  on `/home/keys` updates: the Humble Choice bundle row collapses and an
  individual key row appears with `redeemed_key_val` populated. So Flow B
  is conceptually upstream of Flow A's data model; it just uses a different
  trigger.
* The async delay (3–10 s) suggests the backend is doing real work —
  probably allocating a fresh key from a Steam pool, updating the user's
  order record, and possibly a write through to Steam's partner API. It is
  not just a UI reveal animation.

---

## Discovered API contract (2026-05-04)

Captured live by clicking "GET GAME ON STEAM" on Zero Hour from
`/membership/march-2026` while `humble-bundle-keys diagnose --membership-page march-2026`
recorded the network. Sanitised fixtures live at
`tests/fixtures/choice_claim/`.

The button is **two POSTs back-to-back**, plus two analytics pings we ignore.

### Step 1 — register the user's choice

```
POST https://www.humblebundle.com/humbler/choosecontent
Content-Type: application/x-www-form-urlencoded; charset=UTF-8
X-Requested-With: XMLHttpRequest
Referer: https://www.humblebundle.com/membership/<month-slug>

gamekey=<order_gamekey>
&parent_identifier=initial
&chosen_identifiers[]=<short_id>     ← repeat for each game in one POST
```

Response (200):

```json
{"force_refresh": true, "success": true}
```

Notes:
* The body is form-encoded with PHP/Rails-style array notation —
  `chosen_identifiers[]=foo&chosen_identifiers[]=bar` to claim two games at once.
* `parent_identifier=initial` is what current monthly Choice uses. Older
  legacy tiers might use other values; we should treat anything not seen
  in our fixtures as unknown and refuse to auto-claim.
* `force_refresh: true` is Humble telling its own frontend to re-pull the
  user's data. We treat it as advisory; we'll re-fetch the order detail
  after step 2 anyway.

### Step 2 — reveal the key

```
POST https://www.humblebundle.com/humbler/redeemkey
Content-Type: application/x-www-form-urlencoded; charset=UTF-8
X-Requested-With: XMLHttpRequest

keytype=<machine_name>     ← e.g. "zerohour_row_choice_steam"
&key=<order_gamekey>       ← same gamekey as step 1
&keyindex=0
```

Response (200):

```json
{"key": "XXXXX-XXXXX-XXXXX", "success": true}
```

Notes:
* This is **the same endpoint our existing code already uses** for the
  standard Redeem flow. The only difference for Choice content is that
  step 1 must run first; calling redeemkey directly on unclaimed Choice
  content silently no-ops (this is why our 2026-05-04 dry run reported
  "0 keys revealed" despite hundreds of unclaimed Choice games).
* `keytype` is the tpk's `machine_name` from the order JSON. For Choice
  content that string ends in `_row_choice_<platform>` (e.g.
  `zerohour_row_choice_steam`). The "short identifier" for choosecontent
  is the same string with that suffix stripped — `zerohour`.
* `keyindex` was `0` for the first/only key; we'll trust whatever the
  order's tpk reports.

### Auth + headers

Both calls succeeded with only:
* The session cookie (`_simpleauth_sess`, sent automatically by Playwright)
* `X-Requested-With: XMLHttpRequest` (acts as a soft anti-CSRF check —
  this header can't be set by a cross-site form POST, only by JS in the
  same origin)
* `Referer` set to the membership page

No explicit `CSRF-Prevention-Token` header was observed in the captured
requests. **However**, our diagnose redactor strips that header
defensively, so if the live request did include one it wouldn't show up
in the safe bundle. The implementation should send it if we have a
`csrf_cookie` value (cheap defence in depth, matching what Humble's own
frontend likely does).

### Analytics calls (ignore)

Two no-op POSTs fire alongside the real work:

* `POST /api/v1/analytics/content-choice/content-tile/click/<month_slug>/<short_id>` — fired on card click
* `POST /api/v1/analytics/content-choice/choice/choice/get-game/<month_slug>/<short_id>` — fired on "Get Game on Steam" click

Empty bodies, empty responses, content-length 0. We don't need to call
these to make the claim work — the frontend just sends them as telemetry.

### Bonus discovery: the keys page uses a batched endpoint

While capturing the keys-phase XHRs we saw that `/home/keys` actually
fetches order details via a **batched** endpoint:

```
GET /api/v1/orders?all_tpkds=true&gamekeys=<gk1>&gamekeys=<gk2>&...
```

…with up to 40 gamekeys per request. So the SPA fetches the user's
entire library in roughly 5 calls regardless of size, while our current
`ApiScraper` does one call per order (195 calls in Griffen's library).
**This is a future performance optimization, not blocking Choice claim
work.** Tracked separately.

## Remaining unknowns

These didn't fall out of the capture but matter for safe implementation:

1. **How do we tell apart "claim everything" vs. "pick N of M" Choice tiers?**
   The order JSON likely has a flag or a count; we need to inspect a
   captured order detail blob to find it. Until we've confirmed, our
   implementation should refuse to auto-claim from any month where the
   ratio of `chosen_tpks` to `all_tpks` would matter.
2. **Idempotency on choosecontent.** What happens if we POST it for a
   game already claimed? Likely a no-op (`success: true`, no harm done),
   but we should confirm by replaying the call once via the API after
   the first successful run.
3. **Rate limits.** Probably exists somewhere. Polite delay of 3 s
   between claims (matching the observed 3–10 s UI lag) should keep us
   well below it.

---

## Discovery plan

### Step 1 — capture a single live "Get Game on Steam" click

Run a new diagnose mode that opens `/membership/<some-month>` in a headed
browser, with full XHR + console capture wired up. The user clicks **one**
card, then clicks "GET GAME ON STEAM", then closes the browser. We sanitise
and zip the captured network traffic just like the existing diagnose flow.

CLI:

```bash
humble-bundle-keys diagnose --membership-page march-2026
```

This gives us:

* The full URL and method of whatever `Get Game on Steam` calls.
* The exact request payload (form vs. JSON, field names).
* The response shape — sanitised, with the actual key replaced by
  `REDACTED-KEY` so the bundle is safe to share publicly.
* Any preceding XHRs (e.g. a CSRF token mint, an order detail re-fetch).

### Step 2 — write a deterministic test fixture

Once we have one captured response, drop a sanitised copy into
`tests/fixtures/choice_claim_response.json` and add a parser-only test
that asserts our extractor pulls the right key field out of it.

### Step 3 — implement `ChoiceClaimer`

Add `humble_bundle_keys/choice.py` with a class shaped like `ApiScraper` but
specialised for Flow B:

* Iterate orders that look like Humble Choice subscriptions
  (heuristic: `machine_name` ends with `_choice_storefront`, or
  `human_name` matches `<Month> <Year> Humble Choice`).
* For each unclaimed `tpk` in those orders, call the discovered endpoint.
* Merge the resulting keys into the same `GameKey` model and CSV output
  the rest of the tool already uses.

Wire it into the CLI behind a flag — `--claim-choice` (default off, since
this *does* mutate state on Humble's side and we want users to opt in
explicitly the first time).

### Step 4 — guardrails

* Hard cap on the number of claims per run (`--max-claims`, default 25).
* Polite 3 s delay between claims (matches the observed UI lag).
* On any non-2xx, abort the whole run rather than continuing — surprise
  state changes during a key-claiming workflow are bad.
* Log full request + status for every claim to a run log under
  `~/.humble-bundle-keys/runs/<timestamp>.log` for after-the-fact auditing.

### Step 5 — what we deliberately leave for later

* Driving the "REDEEM" button that hands the key off to Steam. That's a
  separate spec; we'd need to either submit the key to Steam ourselves or
  invoke `steam://open/activateproduct` URL handlers, both of which have
  different risk profiles.
* "GIFT TO FRIEND ON STEAM" — never automate this. Gifts are irrevocable.
* The "SELECT GAMES" picker on legacy Choice tiers where the user chooses
  N of M. Auto-picking on the user's behalf is a product decision they need
  to make per-month; we'll surface those orders in the CSV with a status
  flag (e.g. `requires_manual_selection`) and stop short of claiming.

---

## Open questions for the maintainer

* **How do we know which months are "claim everything" vs. "pick N of M"?**
  Probably a flag on the order, but we won't know for sure until we
  inspect a captured order detail JSON for a legacy month vs. a current month.
* **What's the user-facing copy when we hit the daily / monthly claim limit?**
  Humble probably has rate limits we'll need to handle gracefully.
* **Should we expose a "claim and reveal in one go" flow for non-Choice
  bundles?** Right now Flow A only reveals already-allocated keys; if there
  are bundles in a similar "claim first, reveal second" pattern, we should
  unify the abstraction.

---

## Changelog of this document

* **2026-05-04** — Initial draft after first real-account dry run.
  589 rows captured, 0 newly revealed. Confirmed Flow B exists, captured
  screenshots of the modal in pre/post-claim states.
* **2026-05-04 (later)** — Live capture via `humble-bundle-keys diagnose
  --membership-page march-2026`. Got the wire-level contract for both
  POSTs (choosecontent + redeemkey). Discovered the batched `/api/v1/orders`
  endpoint as a side benefit. Promoted the spec from "discovery" to
  "implementation in progress".
