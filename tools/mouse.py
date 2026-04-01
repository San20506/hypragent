"""Mouse control tool. Implemented in Milestone M2.

System dependency: ydotool + ydotoold daemon (pacman -S ydotool)
Requires: uinput kernel module (modprobe uinput), user in input group.
"""


def move_mouse(x: int, y: int) -> None:
    """Move mouse cursor to absolute screen coordinates.

    Args:
        x: Target X coordinate in screen pixels.
        y: Target Y coordinate in screen pixels.
    """
    # TODO M2: Implement using ydotool mousemove --absolute
    raise NotImplementedError("M2: move_mouse not yet implemented")


def click(x: int, y: int, button: str = "left") -> None:
    """Move to coordinates and click.

    Args:
        x: Target X coordinate.
        y: Target Y coordinate.
        button: "left", "right", or "middle".
    """
    # TODO M2: Implement using ydotool mousemove + ydotool click
    raise NotImplementedError("M2: click not yet implemented")


def double_click(x: int, y: int) -> None:
    """Move to coordinates and double-click.

    Args:
        x: Target X coordinate.
        y: Target Y coordinate.
    """
    # TODO M2: Implement two rapid ydotool clicks
    raise NotImplementedError("M2: double_click not yet implemented")


def drag(from_x: int, from_y: int, to_x: int, to_y: int) -> None:
    """Click and drag from one position to another.

    Args:
        from_x: Drag start X.
        from_y: Drag start Y.
        to_x: Drag end X.
        to_y: Drag end Y.
    """
    # TODO M2: Implement mousedown → mousemove → mouseup sequence
    raise NotImplementedError("M2: drag not yet implemented")


def scroll(x: int, y: int, direction: str, amount: int) -> None:
    """Scroll at coordinates.

    Args:
        x: X coordinate to scroll at.
        y: Y coordinate to scroll at.
        direction: "up" or "down".
        amount: Number of scroll ticks.
    """
    # TODO M2: Implement using ydotool scroll
    raise NotImplementedError("M2: scroll not yet implemented")
