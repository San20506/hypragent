"""Harness abstraction — platform-specific implementations behind Protocol classes.

Usage:
    from harness import detect_harness
    h = detect_harness()
    h.start()
    h.capture_fullscreen()
    h.stop()
"""

import logging
import os
import platform
import shutil

logger = logging.getLogger(__name__)

_HARNESS: "Harness | None" = None  # type: ignore[name-defined]


def detect_harness() -> "Harness":  # type: ignore[name-defined]
    """Auto-detect the correct harness for the current OS/compositor.

    Returns a singleton harness instance for the process lifetime.
    """
    global _HARNESS
    if _HARNESS is not None:
        return _HARNESS

    system = platform.system()
    session = os.environ.get("XDG_SESSION_TYPE", "")

    if system == "Linux" and session == "wayland":
        if shutil.which("hyprctl") or os.path.exists("/usr/bin/hyprctl"):
            from harness.hyprland import HyprlandHarness

            _HARNESS = HyprlandHarness()
            _HARNESS.start()
            return _HARNESS
        from harness.x11 import X11Harness

        _HARNESS = X11Harness()
        return _HARNESS
    elif system == "Linux":
        from harness.x11 import X11Harness

        _HARNESS = X11Harness()
        return _HARNESS
    elif system == "Darwin":
        from harness.macos import MacOSHarness

        _HARNESS = MacOSHarness()
        return _HARNESS
    elif system == "Windows":
        from harness.windows import WindowsHarness

        _HARNESS = WindowsHarness()
        return _HARNESS

    raise RuntimeError(f"No harness available for {system}/{session}")


def reset_harness() -> None:
    """Reset the cached harness singleton (for testing)."""
    global _HARNESS
    _HARNESS = None


from harness.base import Harness, ScreenshotHarness, InputHarness, CompositorHarness

__all__ = [
    "Harness",
    "ScreenshotHarness",
    "InputHarness",
    "CompositorHarness",
    "detect_harness",
    "reset_harness",
]
