"""Browser automation tool via Playwright — Milestone M7.

Python dependency: playwright (uv run playwright install chromium)
Wayland: Chromium launched with --ozone-platform=wayland, headless=False.

Module-level singleton keeps the browser alive across tool calls in a session.
Call browser_close() to tear down between tasks if needed.
"""

import base64

from playwright.sync_api import Browser, Page, Playwright, sync_playwright


_playwright_ctx: Playwright | None = None
_browser: Browser | None = None
_page: Page | None = None


def _ensure_browser() -> Page:
    global _playwright_ctx, _browser, _page
    if _page is None:
        _playwright_ctx = sync_playwright().start()
        _browser = _playwright_ctx.chromium.launch(
            headless=False,
            args=["--ozone-platform=wayland"],
        )
        _page = _browser.new_page()
    return _page


def browser_open(url: str) -> None:
    """Navigate to a URL in the current browser tab."""
    page = _ensure_browser()
    page.goto(url, wait_until="domcontentloaded")


def browser_navigate(url: str) -> None:
    """Navigate the current browser tab to a URL. Alias for browser_open."""
    browser_open(url)


def browser_click(selector: str) -> None:
    """Click an element matching a CSS selector.

    Args:
        selector: CSS selector string, e.g. "button[type=submit]".
    """
    _ensure_browser().click(selector)


def browser_type(selector: str, text: str) -> None:
    """Type text into an input element.

    Args:
        selector: CSS selector for the input element.
        text: Text to type.
    """
    _ensure_browser().fill(selector, text)


def browser_scroll(direction: str, amount: int) -> None:
    """Scroll the current page.

    Args:
        direction: "up" or "down".
        amount: Pixel amount to scroll.
    """
    if direction not in ("up", "down"):
        raise ValueError(f"Unknown direction: {direction!r}. Must be 'up' or 'down'")
    delta = -amount if direction == "up" else amount
    _ensure_browser().evaluate(f"window.scrollBy(0, {delta})")


def browser_screenshot() -> str:
    """Capture a screenshot of the current browser page.

    Returns:
        Base64-encoded PNG string of page screenshot.
    """
    raw = _ensure_browser().screenshot(type="png")
    return base64.b64encode(raw).decode("ascii")


def browser_get_text(selector: str) -> str:
    """Get visible text content of an element.

    Args:
        selector: CSS selector for the element.

    Returns:
        Inner text content of the element.
    """
    return _ensure_browser().inner_text(selector)


def browser_close() -> None:
    """Close the browser and release Playwright resources."""
    global _playwright_ctx, _browser, _page
    if _browser is not None:
        _browser.close()
        _browser = None
        _page = None
    if _playwright_ctx is not None:
        _playwright_ctx.stop()
        _playwright_ctx = None
