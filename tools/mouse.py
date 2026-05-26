"""Mouse control tool — thin dispatcher to active platform harness."""

from harness import detect_harness

_harness = None


def _get_harness():
    global _harness
    if _harness is None:
        _harness = detect_harness()
        _harness.start()
    return _harness


def move_mouse(x: int, y: int) -> None:
    """Move mouse cursor to absolute screen coordinates."""
    _get_harness().move_mouse(x, y)


def click(x: int, y: int, button: str = "left") -> None:
    """Move to coordinates and click."""
    _get_harness().click(x, y, button)


def double_click(x: int, y: int) -> None:
    """Move to coordinates and double-click."""
    _get_harness().double_click(x, y)


def drag(from_x: int, from_y: int, to_x: int, to_y: int) -> None:
    """Click and drag from one position to another."""
    _get_harness().drag(from_x, from_y, to_x, to_y)


def scroll(x: int, y: int, direction: str, amount: int) -> None:
    """Scroll at coordinates."""
    _get_harness().scroll(x, y, direction, amount)
