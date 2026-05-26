"""Keyboard control tool — thin dispatcher to active platform harness."""

from harness import detect_harness

_harness = None


def _get_harness():
    global _harness
    if _harness is None:
        _harness = detect_harness()
        _harness.start()
    return _harness


def type_text(text: str) -> None:
    """Type a string of text."""
    _get_harness().type_text(text)


def press_key(key: str) -> None:
    """Press a single key or key combination."""
    _get_harness().press_key(key)


def hotkey(*keys: str) -> None:
    """Press multiple keys simultaneously."""
    _get_harness().hotkey(*keys)
