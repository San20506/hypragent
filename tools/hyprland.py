"""Hyprland compositor tools — thin dispatcher to active platform harness."""

from harness import detect_harness

_harness = None


def _get_harness():
    global _harness
    if _harness is None:
        _harness = detect_harness()
        _harness.start()
    return _harness


def workspace_list() -> list[dict]:
    """Return all workspaces with id, name, windows, monitor, active."""
    return _get_harness().workspace_list()


def workspace_switch(target: str | int) -> None:
    """Switch to a workspace by id, name, +1, -1, or 'previous'."""
    _get_harness().workspace_switch(target)


def clients() -> list[dict]:
    """Return all open windows with class, title, pid, position, size."""
    return _get_harness().clients()


def active_window() -> dict | None:
    """Return the currently focused window, or None if no window is focused."""
    return _get_harness().active_window()


def focus_window(target: str) -> None:
    """Focus a window by class or address."""
    _get_harness().focus_window(target)
