"""Keyboard control tool — Milestone M2.

System dependency: ydotool + ydotoold daemon (pacman -S ydotool)
Requires: uinput kernel module (modprobe uinput), user in input group.
"""

import os
import subprocess

YDOTOOL_SOCKET = "/run/user/1000/.ydotool_socket"


def _ydotool(*args: str) -> None:
    env = {**os.environ, "YDOTOOL_SOCKET": YDOTOOL_SOCKET}
    result = subprocess.run(["ydotool", *args], capture_output=True, text=True, env=env)
    if result.returncode != 0:
        raise RuntimeError(f"ydotool {args[0]} failed: {result.stderr.strip()}")


def type_text(text: str) -> None:
    """Type a string of text character by character.

    Args:
        text: The text to type.
    """
    if not text:
        raise ValueError("text must not be empty")
    # --delay 20ms prevents dropped chars under load; -- separates flags from text
    _ydotool("type", "--delay", "20", "--", text)


def press_key(key: str) -> None:
    """Press a single key or key combination.

    Args:
        key: Key string, e.g. "Return", "Escape", "ctrl+c", "super+l".
             Uses X11 keysym names compatible with ydotool.
    """
    _ydotool("key", key)


def hotkey(*keys: str) -> None:
    """Press multiple keys simultaneously.

    Args:
        *keys: Key names to press together, e.g. hotkey("ctrl", "shift", "t").
    """
    if not keys:
        raise ValueError("at least one key required")
    press_key("+".join(keys))
