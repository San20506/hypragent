"""Screenshot capture tool. Milestone M1.

Thin dispatcher — delegates to the active platform harness.
"""

from tools import _get_harness


def capture_fullscreen() -> str:
    """Capture the entire screen and return as base64-encoded PNG string."""
    return _get_harness().capture_fullscreen()


def capture_region(x: int, y: int, width: int, height: int) -> str:
    """Capture a screen region and return as base64-encoded PNG string."""
    return _get_harness().capture_region(x, y, width, height)


def save_screenshot(path: str) -> None:
    """Capture fullscreen and save to file."""
    _get_harness().save_screenshot(path)
