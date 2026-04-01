"""Keyboard control tool. Implemented in Milestone M2.

System dependency: ydotool + ydotoold daemon (pacman -S ydotool)
Requires: uinput kernel module (modprobe uinput), user in input group.
"""


def type_text(text: str) -> None:
    """Type a string of text character by character.

    Args:
        text: The text to type. Handles unicode via wl-clipboard paste strategy.
    """
    # TODO M2: Implement using ydotool type or wl-copy + paste hotkey
    raise NotImplementedError("M2: type_text not yet implemented")


def press_key(key: str) -> None:
    """Press a single key or key combination.

    Args:
        key: Key string, e.g. "Return", "Escape", "ctrl+c", "super+l".
             Uses X11 keysym names compatible with ydotool.
    """
    # TODO M2: Implement using ydotool key
    raise NotImplementedError("M2: press_key not yet implemented")


def hotkey(*keys: str) -> None:
    """Press multiple keys simultaneously.

    Args:
        *keys: Key names to press together, e.g. hotkey("ctrl", "shift", "t").
    """
    # TODO M2: Implement as ydotool key with combined keysym string
    raise NotImplementedError("M2: hotkey not yet implemented")
