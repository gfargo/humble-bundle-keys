"""Humble Choice claiming for the redesigned (Next.js) Humble site.

Humble rebuilt the store in November 2026: the old /home/keys table and the
JSON API are gone, and the library is now a Next.js app. This module drives the
new pages the same way a person does:

1. Open /home/library and switch to the "Purchased" tab. The tab's
   filterUserLibrary server action returns the purchased items, each with its
   title and a subTitle such as "October 2026 Humble Choice".
2. Open each item's content page. A revealed key is part of the page's React
   Server Components payload (``redemptionData.keyFormatted``); an unrevealed
   one shows a reveal control that we click.
3. Return GameKey rows in the same shape the rest of the package uses.

Everything here is best-effort against a moving target: selectors and the
action payload are matched by what they are (a tab named "Purchased", a button
whose label mentions reveal), not by generated ids.
"""

from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import dataclass
from typing import Any

from playwright.sync_api import BrowserContext, Page

from humble_bundle_keys.models import GameKey

log = logging.getLogger(__name__)

LIBRARY_URL = "https://www.humblebundle.com/home/library"
CONTENT_URL = "https://www.humblebundle.com/home/library/content/"

MONTH_NAMES = [
    "january", "february", "march", "april", "may", "june",
    "july", "august", "september", "october", "november", "december",
]

REVEAL_LABEL = re.compile(r"\b(reveal|show key|get key|claim)\b", re.IGNORECASE)
KEY_PATTERN = re.compile(r"[A-Z0-9]{4,5}-[A-Z0-9]{4,5}-[A-Z0-9]{4,5}")


@dataclass
class MonthItem:
    """One purchased Choice entry as the library lists it."""

    entitlement_id: str
    title: str
    subtitle: str
    url: str


@dataclass
class ItemState:
    """What a content page says about one entry."""

    title: str
    subtitle: str
    platform: str
    key: str
    redeemed_at: str
    deadline: str


def slug_to_display(slug: str) -> str | None:
    """Map ``october-2026`` to ``October 2026``."""
    match = re.match(r"^([a-z]+)-(\d{4})$", slug.strip().lower())
    if not match or match.group(1) not in MONTH_NAMES:
        return None
    return f"{match.group(1).capitalize()} {match.group(2)}"


def _flight_payload(html: str) -> str:
    """Concatenate the inline RSC flight chunks of an HTML page."""
    marker = "self.__next_f.push([1,"
    index = 0
    chunks: list[str] = []
    decoder = json.JSONDecoder()
    while True:
        offset = html.find(marker, index)
        if offset < 0:
            break
        start = offset + len(marker)
        try:
            chunk, consumed = decoder.raw_decode(html[start:])
        except ValueError:
            index = start + 1
            continue
        chunks.append(chunk)
        index = start + consumed
    return "".join(chunks)


def _walk(value: Any, predicate):
    if isinstance(value, dict):
        if predicate(value):
            return value
        for child in value.values():
            found = _walk(child, predicate)
            if found is not None:
                return found
    elif isinstance(value, list):
        for child in value:
            found = _walk(child, predicate)
            if found is not None:
                return found
    return None


def _flight_rows(payload: str) -> list[Any]:
    """Parse ``<id>:<json>`` and ``<id>:T<hex-bytes>,<text>`` rows."""
    data = payload.encode("utf-8")
    values: list[Any] = []
    index = 0
    while index < len(data):
        if data[index:index + 1] == b"\n":
            index += 1
            continue
        colon = data.find(b":", index)
        if colon < 0:
            break
        start = colon + 1
        if data[start:start + 1] == b"T":
            comma = data.find(b",", start)
            if comma < 0:
                break
            try:
                length = int(data[start + 1:comma], 16)
            except ValueError:
                break
            end = comma + 1 + length
            values.append(data[comma + 1:end].decode("utf-8", "replace"))
            index = end
            continue
        newline = data.find(b"\n", start)
        if newline < 0:
            raw = data[start:]
            index = len(data)
        else:
            raw = data[start:newline]
            index = newline
        raw = raw.replace(b"$undefined", b"null")
        try:
            values.append(json.loads(raw))
        except ValueError:
            continue
    return values


def list_month_items(context: BrowserContext, slug: str, page: Page | None = None) -> list[MonthItem]:
    """Return the purchased items of one Choice month.

    The Purchased tab loads its list through the filterUserLibrary server
    action; we read the action's JSON responses instead of scraping cards.
    """
    display = slug_to_display(slug)
    if display is None:
        raise ValueError(f"cannot parse membership slug {slug!r}")

    own_page = page is None
    page = page or context.new_page()
    results: list[dict[str, Any]] = []

    def on_response(response):
        request = response.request
        if request.method != "POST" or not request.headers.get("next-action"):
            return
        try:
            text = response.text()
        except Exception:
            return
        # The action answers as a React flight payload: "1:{"results":[...]}".
        for line in text.split("\n"):
            if not line.startswith("1:"):
                continue
            try:
                body = json.loads(line[2:])
            except ValueError:
                continue
            if isinstance(body, dict) and isinstance(body.get("results"), list):
                results.extend(body["results"])

    page.on("response", on_response)
    try:
        page.goto(LIBRARY_URL, wait_until="domcontentloaded", timeout=60_000)
        page.wait_for_timeout(6_000)
        clicked = False
        try:
            tab = page.get_by_role("tab", name="Purchased").first
            tab.wait_for(state="visible", timeout=15_000)
            tab.click(timeout=10_000)
            clicked = True
        except Exception:
            clicked = False
        if not clicked:
            for element in page.query_selector_all("button, [role=tab], a"):
                try:
                    text = re.sub(r"\s+", " ", (element.inner_text() or "")).strip()
                except Exception:
                    continue
                if text == "Purchased":
                    element.click(timeout=10_000)
                    clicked = True
                    break
        if not clicked:
            log.warning("Could not find the Purchased tab on the library page")
        page.wait_for_timeout(8_000)
        # Load further pages if the list is paginated.
        for _ in range(6):
            before = len(results)
            try:
                page.mouse.wheel(0, 4000)
            except Exception:
                pass
            page.wait_for_timeout(2_500)
            if len(results) == before:
                break
    finally:
        page.remove_listener("response", on_response)

    items: list[MonthItem] = []
    seen: set[str] = set()
    for entry in results:
        subtitle = str(entry.get("subTitle") or "")
        if display.lower() not in subtitle.lower():
            continue
        entitlement_id = str(entry.get("id") or "")
        if not entitlement_id or entitlement_id in seen:
            continue
        seen.add(entitlement_id)
        items.append(MonthItem(
            entitlement_id=entitlement_id,
            title=str(entry.get("title") or ""),
            subtitle=subtitle,
            url=CONTENT_URL + entitlement_id,
        ))

    if own_page:
        page.close()
    log.info("Found %d item(s) for %s", len(items), display)
    return items


def read_item_state(page: Page, url: str) -> ItemState | None:
    """Read the key and metadata of one content page."""
    page.goto(url, wait_until="domcontentloaded", timeout=60_000)
    page.wait_for_timeout(2_000)
    html = page.content()
    payload = _flight_payload(html)
    if not payload:
        return None

    container = _walk(_flight_rows(payload), lambda value: isinstance(value.get("entitlements"), dict))
    if container is None:
        return None

    entitlements = container["entitlements"]
    keys = entitlements.get("keys") or []
    if not isinstance(keys, list) or not keys:
        return None

    entry = keys[0]
    redemption = entry.get("redemptionData") or {}
    key = str(redemption.get("keyFormatted") or "")
    if not key:
        # Fall back to a key-shaped string on the page.
        match = KEY_PATTERN.search(page.inner_text("body"))
        key = match.group(0) if match else ""

    return ItemState(
        title=str(entry.get("title") or ""),
        subtitle=str(entry.get("subTitle") or ""),
        platform=str(entry.get("type") or ""),
        key=key,
        redeemed_at=str(entry.get("redeemedAt") or ""),
        deadline=str(entry.get("unavailableAfter") or ""),
    )


def reveal_item(page: Page, url: str) -> bool:
    """Click the reveal control on a content page. Returns True on success."""
    page.goto(url, wait_until="domcontentloaded", timeout=60_000)
    page.wait_for_timeout(2_000)

    candidates = page.query_selector_all("button, a, [role=button]")
    for element in candidates:
        try:
            text = re.sub(r"\s+", " ", (element.inner_text() or "")).strip()
        except Exception:
            continue
        if not text or not REVEAL_LABEL.search(text):
            continue
        try:
            element.scroll_into_view_if_needed()
            element.click(timeout=8_000)
        except Exception as exc:
            log.warning("Reveal click failed for %s: %s", url, str(exc)[:120])
            continue
        page.wait_for_timeout(4_000)
        state = read_item_state(page, url)
        if state and state.key:
            return True
    return False


def claim_month(
    context: BrowserContext,
    slug: str,
    *,
    dry_run: bool = False,
    max_claims: int = 100,
    delay_s: float = 1.0,
) -> tuple[list[GameKey], int]:
    """Claim/reveal one Choice month.

    Returns ``(rows, revealed_this_run)``. ``rows`` includes already-revealed
    keys, so a scheduled run can queue them again after a partial failure.
    """
    page = context.new_page()
    rows: list[GameKey] = []
    revealed = 0
    try:
        items = list_month_items(context, slug, page=page)
        for index, item in enumerate(items):
            if index >= max_claims:
                break
            state = read_item_state(page, item.url)
            if state is None:
                log.warning("Could not read %s (%s)", item.title, item.url)
                continue
            if not state.key and not dry_run:
                if reveal_item(page, item.url):
                    revealed += 1
                    state = read_item_state(page, item.url) or state
            rows.append(GameKey(
                game_title=state.title or item.title,
                platform=state.platform,
                key=state.key,
                bundle_name=state.subtitle or item.subtitle,
                bundle_date="",
                redemption_deadline=state.deadline,
                redeemed_on_humble=bool(state.redeemed_at),
                os_support="",
                humble_url=item.url,
            ))
            if delay_s:
                time.sleep(delay_s)
    finally:
        page.close()
    return rows, revealed
