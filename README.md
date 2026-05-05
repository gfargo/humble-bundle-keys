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

## What it does

1. **Logs you in once** in a real Chromium window (so 2FA works normally) and saves the session for reuse.
2. **Walks every order in your library** via Humble's private JSON API.
3. **Reveals already-allocated keys** by calling Humble's "Redeem" endpoint on each unrevealed entry.
4. **Claims Humble Choice subscription games** via API or browser-driven flows.
5. **Writes everything to a CSV** with one row per key.

## What it doesn't do

- ❌ Log into Steam, GOG, Origin, or any other store
- ❌ Store your Humble password
- ❌ Make purchases or modify account settings
- ❌ Gift games to friends (gifts are irrevocable)

---

## Three extraction modes

| Mode | Flag | Speed | Catches |
| --- | --- | --- | --- |
| Default reveal | *(none)* | Fast | Bundle keys, revealed Choice/Monthly keys |
| Choice API claim | `--claim-choice` | Fast | Modern Choice months (key not yet allocated) |
| Browser claim | `--browser-claim` | Slow | Everything, including legacy "pick N of M" months |

```bash
# Combined run: API reveal + browser claim, all in one go.
humble-bundle-keys --browser-claim --max-claims 200 --merge -v
```

📖 **[Full documentation →](https://github.com/gfargo/humble-bundle-keys/wiki)**

---

## Documentation

Comprehensive documentation is available on the **[GitHub Wiki](https://github.com/gfargo/humble-bundle-keys/wiki)**:

- **[Installation](https://github.com/gfargo/humble-bundle-keys/wiki/Installation)** — Install the tool and dependencies
- **[Quick Start](https://github.com/gfargo/humble-bundle-keys/wiki/Quick-Start)** — First run walkthrough
- **[Authentication](https://github.com/gfargo/humble-bundle-keys/wiki/Authentication)** — Sessions, CI usage, troubleshooting login
- **[Extraction Modes](https://github.com/gfargo/humble-bundle-keys/wiki/Extraction-Modes)** — The three modes explained in depth
- **[CLI Reference](https://github.com/gfargo/humble-bundle-keys/wiki/CLI-Reference)** — All flags and subcommands
- **[Output Format](https://github.com/gfargo/humble-bundle-keys/wiki/Output-Format)** — CSV columns and merge behavior
- **[What's Claimable](https://github.com/gfargo/humble-bundle-keys/wiki/What's-Claimable)** — Key categories and recoverability
- **[Troubleshooting](https://github.com/gfargo/humble-bundle-keys/wiki/Troubleshooting)** — Common errors and fixes
- **[Architecture](https://github.com/gfargo/humble-bundle-keys/wiki/Architecture)** — System design and module map
- **[Contributing](https://github.com/gfargo/humble-bundle-keys/wiki/Contributing)** — Dev setup, tests, filing bugs

---

## Common flags

| Flag | What it does |
| --- | --- |
| `--dry-run` | Read-only. Walk everything, don't reveal or claim. |
| `--browser-claim` | Drive membership pages to claim Choice games. |
| `--max-claims N` | Hard cap on claims per run. Default 100. |
| `--merge` | Merge with existing CSV instead of overwriting. |
| `-v` / `-vv` | Bump console verbosity. |
| `-y` / `--yes` | Skip confirmation prompts. |

Run `humble-bundle-keys --help` for the full list, or see the [CLI Reference](https://github.com/gfargo/humble-bundle-keys/wiki/CLI-Reference).

---

## Troubleshooting

See the **[Troubleshooting guide](https://github.com/gfargo/humble-bundle-keys/wiki/Troubleshooting)** for common issues. The short version:

- **Cloudflare 403s**: Transient 403s are now auto-retried (up to 3 attempts with backoff). If you see persistent HTML errors, re-run normally.
- **Selector breakage**: Run `humble-bundle-keys diagnose -v` and attach `safe-to-share.zip` to an issue.
- **Session expired**: `humble-bundle-keys logout && humble-bundle-keys`
- **Choice items detected**: The summary now prints a copy-pasteable re-run command with the exact flags needed.

---

## Contributing

Issues and PRs welcome. See the **[Contributing guide](https://github.com/gfargo/humble-bundle-keys/wiki/Contributing)** for dev setup and conventions.

```bash
git clone https://github.com/gfargo/humble-bundle-keys.git
cd humble-bundle-keys
uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"
playwright install chromium
pytest
```

See also [`CONTRIBUTING.md`](CONTRIBUTING.md) and [`SECURITY.md`](SECURITY.md).

---

## Disclaimer

This tool automates browser actions you could perform yourself. It is **not affiliated with or endorsed by Humble Bundle**. Automated access may be against Humble's Terms of Service — use at your own risk. The polite delay between actions exists to keep traffic patterns reasonable.

The tool will never: redeem keys outside humblebundle.com, make purchases, modify account settings, or gift games to friends.

---

## License

[MIT](LICENSE)
