# What's claimable, what isn't

After a complete `humble-bundle-keys` run, the summary may show a "Reveals that returned no key" line with a category breakdown. This page explains what each category means and why some are structurally outside the tool's reach.

The tool categorizes each unrevealed entry by inspecting its `tpk.machine_name` (see `humble_bundle_keys/choice.py::categorize_keytype`).

## ✅ Recoverable categories

### `choice` — Modern Humble Choice content

**Pattern**: `*_choice_steam`, `*_row_choice_steam`, `*_naeu_choice_steam`, `*_choice_epic_keyless`, and the typo'd `*_hoice_steam`.

These are subscription games where the key hasn't been allocated yet on Humble's side. The tool can claim them via either:

- `--claim-choice` — fast, API-only, two-step `POST /humbler/choosecontent` then `POST /humbler/redeemkey`
- `--browser-claim` — slower, drives the membership page UI, catches cases the API path can't

If a run shows `choice: N` in the silent-no-key summary, re-run with one of those flags.

### `monthly` — Legacy Humble Monthly

**Pattern**: `*_monthly_steam`.

These are pre-Choice subscription games. Most are pre-allocated and just hidden behind the standard Redeem button — they're handled by the default reveal flow without any extra flag.

A small number get stuck in a "Humble says I claimed this but no key materializes" state. Causes are usually one of:

- The key was gifted to a friend and Humble's bookkeeping wasn't updated
- The game was refunded / removed from your account but the row still exists
- The key expired upstream and Humble hasn't cleaned the entry

These are unfixable from this tool — they need a Humble support ticket.

## ❌ Structurally unrecoverable categories

### `keyless` — Epic Games "keyless" delivery

**Pattern**: `*_epic_keyless`.

Some Humble Bundle games are delivered to your Epic Games library directly instead of via a redemption key. There is **no key to extract** — Humble's UI just shows a "Get on Epic" button that links your accounts. We don't and can't write anything to the CSV for these.

If you want to claim them, click them manually on Humble's site.

### `freegame` — Free-game promos

**Pattern**: `*_freegame_steam`.

Promotional free-game claims from Humble's storefront (e.g. "DESYNC", "Kingdom: Classic" giveaways). These use a different redemption endpoint than `/humbler/redeemkey`. We could potentially support them in a future version, but they're rare enough that nobody has needed it yet.

If `freegame: N` shows up and you care, file a feature request and include the order's `product.machine_name`.

### `softwarebundle` — Audio/software vendor bundles

**Pattern**: `*_softwarebundle`.

Audio software bundles (Mixcraft, Voltage Modular, Pianissimo Grand Piano, etc.) use vendor-specific redemption flows that vary per publisher. There's no single endpoint we could call — each vendor has its own activation page, account creation requirements, license file delivery, etc.

These need to be claimed manually on the vendor's site.

### `voucher` — Store-credit vouchers

**Pattern**: `*_voucher`, `*_giftcard`.

Store-credit vouchers (e.g. "Synty Store $10 USD Voucher") are not Steam-shaped keys. They're URLs / codes for the vendor's storefront. We could capture the URL but not into the same CSV as game keys without making the schema awkward.

If you want voucher tracking, file a feature request.

### `bundle` — Plain bundle key (should already work)

**Pattern**: `*_bundle_steam`, `*_bundle_<other>`.

Regular Humble Bundle game keys. These should work via the default reveal flow. If `bundle: N` shows up in the silent-no-key summary, that's surprising and worth investigating — open an issue with the affected `tpk.machine_name` and `order.machine_name` (the summary shows them).

### `other` — Unrecognized

Anything that doesn't match a known pattern. If this comes up, paste the line into a GitHub issue and we'll add it to the categorizer.

---

## The bigger picture

The categories above split roughly into two halves:

**Auto-claimable** (`choice`, `monthly`, most `bundle`) — the majority of any account's library. These are standard Steam-shaped keys delivered through Humble's own redemption flow and the tool can extract them all.

**Structurally manual** (`keyless`, `softwarebundle`, `voucher`, some `freegame`) — these aren't bugs in the tool; they're entries that don't *have* a Steam-shaped key to extract. Epic keyless games go directly to your Epic library with no key involved; software bundles route through per-vendor activation pages; vouchers are URLs not keys. No automated tool can change that without doing fundamentally different work per category.

The practical takeaway: after a complete `humble-bundle-keys --browser-claim` run, you'll see most of your library in the CSV. The handful of holdouts in the summary will be categorized so you know which (if any) need follow-up, vs. which are just inherent to how Humble distributes that specific item.
