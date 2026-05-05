---
name: Selector / DOM broken
about: Humble redesigned something and the tool stopped finding rows / cards / buttons
title: '[selector] '
labels: bug, selectors
---

## Symptom

<!-- Choose one:
     - 0 rows found on /home/keys
     - 0 cards found on /membership/<slug>
     - "Get Game on Steam" button not visible
     - Key field never populated within timeout
     - Other (describe) -->

## Date you noticed it

<!-- Approximate. Helps correlate with Humble's redesign cadence. -->

## Diagnose bundle

The fastest path to a fix is a sanitized diagnose bundle. **Run one of these** depending on what's broken:

```bash
# /home/keys regression:
humble-bundle-keys diagnose -v

# /membership/<slug> regression:
humble-bundle-keys diagnose --membership-page <some-month-slug> -v
```

This produces `humble-diagnose/diagnose-<timestamp>/safe-to-share.zip`.

**Before attaching, spot-check the zip:**

- Open a couple of the JSON files in `api/`. Real keys (anything looking like `XXXXX-XXXXX-XXXXX`) should appear as `REDACTED-KEY`.
- Check email addresses appear as `REDACTED@example.com`.
- Check `?gamekey=` URL params appear as `?gamekey=REDACTED-GAMEKEY`.
- Check `Cookie` and `Authorization` headers are not present in the JSON header dumps.

If any sensitive value slipped through, **don't attach** — open a [security issue](../SECURITY.md) instead.

## Attached bundle

<!-- Drag-and-drop your safe-to-share.zip here, or link to a paste/gist. -->

## Anything else

<!-- Custom flags you're using? Particular months that fail vs. work? Account quirks? -->
