"""Browser automation tool via Playwright — Milestone M7.

Safety: URLs are validated before navigation. Dangerous schemes (file://,
javascript:, data:) and private IP ranges are blocked to prevent SSRF
and local file access.

Note: Uses Playwright sync API. Converting to async is a future improvement
that requires refactoring the dispatch chain (dispatch_tool, _dispatch_tool,
execute_plan) to be fully async.
"""

import base64
import ipaddress
import platform
from urllib.parse import urlparse

_playwright_ctx = None
_browser = None
_page = None


def _ensure_browser():
    global _playwright_ctx, _browser, _page
    if _page is not None:
        return _page

    from playwright.sync_api import sync_playwright

    _playwright_ctx = sync_playwright().start()
    _browser = _playwright_ctx.chromium.launch()
    _page = _browser.new_page()
    return _page


# Blocked URL schemes — these can access local files or execute code
_BLOCKED_SCHEMES = {"file", "javascript", "data", "vbscript", "about"}

# Private IP ranges that should not be accessible via browser
_PRIVATE_IP_RANGES = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("169.254.0.0/16"),  # Link-local / cloud metadata
    ipaddress.ip_network("127.0.0.0/8"),  # Loopback
    ipaddress.ip_network("::1/128"),  # IPv6 loopback
    ipaddress.ip_network("fc00::/7"),  # IPv6 private
]


def _validate_url(url: str) -> None:
    """Validate that a URL is safe to navigate to.

    Args:
        url: URL to validate.

    Raises:
        ValueError: If URL uses a blocked scheme or targets private IPs.
    """
    parsed = urlparse(url)

    # Check scheme
    if parsed.scheme.lower() in _BLOCKED_SCHEMES:
        raise ValueError(
            f"URL scheme {parsed.scheme!r} is blocked for security reasons. "
            f"Blocked schemes: {', '.join(sorted(_BLOCKED_SCHEMES))}"
        )

    # Only allow http and https
    if parsed.scheme.lower() not in {"http", "https"}:
        raise ValueError(
            f"URL scheme {parsed.scheme!r} is not allowed. Only http and https are permitted."
        )

    # Check hostname for private IPs
    hostname = parsed.hostname
    if hostname:
        # Try to parse as IP address
        try:
            ip = ipaddress.ip_address(hostname)
            for network in _PRIVATE_IP_RANGES:
                if ip in network:
                    raise ValueError(
                        f"URL targets private IP range {network} which is blocked "
                        f"to prevent SSRF attacks."
                    )
        except ValueError as e:
            # Not an IP address, could be a hostname
            # Check for common private hostnames
            if hostname in {"localhost", "metadata.google.internal"}:
                raise ValueError(
                    f"Hostname {hostname!r} is blocked to prevent SSRF attacks."
                )
            # Re-raise if it was our ValueError
            if "private IP" in str(e) or "blocked" in str(e):
                raise


def browser_open(url: str) -> None:
    """Navigate to a URL in the current browser tab.

    Safety: URL is validated against blocked schemes and private IP ranges.
    """
    _validate_url(url)
    page = _ensure_browser()
    page.goto(url, wait_until="domcontentloaded")


def browser_navigate(url: str) -> None:
    """Navigate the current browser tab to a URL. Alias for browser_open."""
    browser_open(url)


def browser_click(selector: str) -> None:
    """Click an element matching a CSS selector.

    Args:
        selector: CSS selector string (e.g. "#submit-btn", ".login-form > button").
    """
    _ensure_browser().click(selector)


def browser_type(selector: str, text: str) -> None:
    """Type text into an input field matching a CSS selector.

    Args:
        selector: CSS selector for the input element.
        text: Text to type.
    """
    _ensure_browser().fill(selector, text)


def browser_scroll(direction: str, amount: int) -> None:
    """Scroll the current page.

    Args:
        direction: "up" or "down".
        amount: Pixels to scroll.
    """
    delta = amount if direction == "down" else -amount
    _ensure_browser().evaluate(f"window.scrollBy(0, {delta})")


def browser_screenshot() -> str:
    """Capture a screenshot of the current browser page.

    Returns:
        Base64-encoded PNG image.
    """
    raw = _ensure_browser().screenshot(type="png")
    return base64.b64encode(raw).decode("ascii")


def browser_get_text(selector: str) -> str:
    """Get visible text content of an element.

    Args:
        selector: CSS selector for the element.

    Returns:
        Text content of the element.
    """
    return _ensure_browser().inner_text(selector)


def browser_close() -> None:
    """Close the browser and release Playwright resources."""
    global _playwright_ctx, _browser, _page
    if _browser:
        _browser.close()
        _browser = None
    if _playwright_ctx:
        _playwright_ctx.stop()
        _playwright_ctx = None
    _page = None
