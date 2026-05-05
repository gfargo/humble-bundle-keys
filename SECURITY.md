# Security policy

## Reporting a vulnerability

If you discover a security issue in `humble-bundle-keys` — particularly anything that could leak a user's session cookie, Steam keys, or other sensitive data — please **do not open a public GitHub issue**. Instead, email the maintainer directly:

> testuser@example.com — subject line `[humble-bundle-keys security]`

I'll acknowledge within 72 hours and aim to ship a fix within two weeks. If the fix requires coordinated disclosure (e.g. an issue that affects existing user CSVs), we'll agree on a public-disclosure date together.

## What this tool handles that's sensitive

The maintainer cares about three classes of secret living inside this codebase:

1. **The user's Humble session cookie** (`_simpleauth_sess`). Persisted to `~/.humble-bundle-keys/storage_state.json` after login and used by every subsequent run. Anyone with this file can act as the user on humblebundle.com until it expires.
2. **Game keys** themselves — the `XXXXX-XXXXX-XXXXX` strings revealed by the tool. Anyone with a valid key can claim the game on Steam, gifting it to themselves.
3. **Order gamekeys** — Humble's internal 16-char identifiers used in URL parameters (e.g. `?gamekey=ABC123…`). Less catastrophic than the above but identify a specific purchase.

## What the tool does to protect them

- **Session cookie** is persisted with `0700` directory permissions on the parent `~/.humble-bundle-keys/` and never logged in any form.
- **Game keys** are written only to the user's chosen CSV path (default `./humble-bundle-keys.csv`) and to the on-disk run log at DEBUG level. The run log retains the last 20 runs by default — pruned automatically. **Note**: if you commit the CSV or the run log to a public repo, your keys are exposed. The `.gitignore` excludes both shapes by default.
- **The diagnose bundle workflow** has a dedicated sanitizer (`humble_bundle_keys/diagnose.py`) that strips: keys (regex `XXXXX-XXXXX-XXXXX` or 12+ alnum), emails (regex), `gamekey=` URL parameters, and a fixed list of sensitive HTTP headers (`Cookie`, `Set-Cookie`, `Authorization`, `Proxy-Authorization`, `CSRF-Prevention-Token`, `X-CSRF-Token`, `X-CSRFToken`, `X-XSRF-Token`). The sanitizer has 14 unit tests covering every category. **The `raw/` folder is never sanitized** — only the `safe-to-share/` copy. Users are warned to share only the latter.
- **Trace files** (`trace.zip`) from Playwright captures are *deliberately not* included in `safe-to-share/` because their HAR / DOM-snapshot contents are very hard to sanitize reliably. They stay in `raw/` for local replay only.

## Threat model and explicit non-goals

- The tool does **not** defend against a malicious user on the same machine. If someone has read access to your `~/.humble-bundle-keys/` directory, they have your session.
- The tool does **not** defend against a compromised PyPI / GitHub release. Pinning to a known-good version and verifying installs is the user's responsibility (CI uses trusted publishing for what protection it can offer).
- The tool does **not** attempt to evade Humble's rate-limiting or bot-detection measures. The polite delays and "use the same browser the user uses" approach are designed to look like a genuine human session, not to bypass legitimate enforcement.

## Responsible-use scope

This tool automates browser actions that any account-holder could perform manually. It does not:

- Execute trades, transfer money, or initiate any financial action on behalf of the user.
- Click "Gift to Friend on Steam" — even though the affordance exists in the modal, the tool deliberately never targets that selector.
- Submit support tickets, post comments, or contact other users.
- Modify account settings or shipping addresses.

If you find a way to make the tool perform any of the above, that's a security bug — please report it via the email above.
