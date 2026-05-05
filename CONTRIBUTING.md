# Contributing

Thanks for poking at this project. The most fragile parts of `humble-bundle-keys` are the DOM selectors (`humble_bundle_keys/scraper.py`, `humble_bundle_keys/browser_choice.py`) and the assumed shapes of Humble's undocumented JSON API (`humble_bundle_keys/api.py`). Both will eventually break when Humble redesigns something. The fastest path to a fix in those cases is a captured **diagnose bundle**, described below.

## Dev setup

```bash
git clone https://github.com/gfargo/humble-bundle-keys.git
cd humble-bundle-keys

# Using uv (recommended):
uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"

# Or plain pip:
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# Browser engine (Playwright handles this for you):
playwright install chromium
```

## Running tests + lint

```bash
# 121+ unit tests — should run in well under a second.
pytest

# Lint
ruff check humble_bundle_keys tests

# Lint with autofix
ruff check --fix humble_bundle_keys tests
```

There are no live-account tests in CI — every test in `tests/` runs without a network or browser. Tests that genuinely need a real Humble account should be marked `@pytest.mark.live` and excluded from the default `pytest` run.

## Filing a "selector broken" bug

If the tool stops finding rows / cards / buttons after a Humble redesign, the most useful thing you can attach is a sanitized diagnose bundle. Run:

```bash
# For /home/keys regressions:
humble-bundle-keys diagnose -v

# For /membership/<slug> regressions:
humble-bundle-keys diagnose --membership-page <some-month-slug> -v
```

This produces a `humble-diagnose/diagnose-<timestamp>/` directory with:

- `raw/` — contains your real keys. **Do NOT share.** Local debugging only.
- `safe-to-share/` — sanitized: keys → `REDACTED-KEY`, emails → `REDACTED@example.com`, gamekey URL params → `REDACTED-GAMEKEY`, auth headers stripped.
- `safe-to-share.zip` — convenience zip of the safe folder.

Spot-check the sanitized files (open a few of the JSON / HTML files and confirm no `XXXXX-XXXXX-XXXXX`-shaped strings or @ characters remain), then attach `safe-to-share.zip` to the GitHub issue.

The sanitizer has 14 unit tests covering every category we know about. If you find something it missed, that's itself a bug worth filing — check `humble_bundle_keys/diagnose.py` and `tests/test_diagnose_sanitiser.py`.

## Filing a "Humble Choice month X has unclaimed games we can't see" bug

If `--browser-claim` is reporting `0 cards found` on a month you know has unclaimed games, please attach:

1. The output of `humble-bundle-keys --browser-claim --dry-run --membership-only <slug> -vv`
2. A `humble-bundle-keys diagnose --membership-page <slug>` bundle

## Adding tests when you change a selector

If you fix a selector and have access to a fresh diagnose bundle:

1. Drop the relevant `safe-to-share/membership/01-initial.html` into `tests/fixtures/<topic>/<name>.html`.
2. Add a fixture-based test that loads the file via `page.set_content(...)` (or BeautifulSoup if you can avoid Playwright entirely) and asserts the new selector matches.

Pure parsing helpers (in `_extract_tpk`, `categorize_keytype`, `derive_membership_slug`, etc.) should always have direct unit tests — they're the cheapest layer to test.

## PR conventions

- Bump `version` in both `pyproject.toml` and `humble_bundle_keys/__init__.py`. The release workflow checks they match.
- Add a `CHANGELOG.md` entry under a new version heading. Keep tone consistent with existing entries: explain the *user-visible* change, not the implementation, plus what symptom this fixes if it's a bug.
- Run `ruff check humble_bundle_keys tests` and `pytest` before pushing.

## Releasing

Tag-driven via `.github/workflows/release.yml`:

```bash
# After merging the version bump:
git tag v0.4.0
git push origin v0.4.0
```

That triggers: build sdist + wheel → smoke-test the wheel → publish to PyPI via trusted publishing → create a GitHub Release with the wheel attached and notes pulled from CHANGELOG.md.

PyPI publishing uses [trusted publishing](https://docs.pypi.org/trusted-publishers/) — no API tokens stored as secrets. The `pypi` environment in the workflow corresponds to the `pypi.org/p/humble-bundle-keys` project's trusted-publishing config.
