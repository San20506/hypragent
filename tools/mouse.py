"""Mouse control tool — evdev/UInput virtual mouse device.

Uses the DeviceManager singleton (agent/device_manager.py) to inject absolute
mouse positioning via EV_ABS events. No subprocess calls — events go directly
to the Linux input subsystem via the HyprAgent Mouse virtual device.
"""

import time

from evdev import ecodes as e

from agent.device_manager import devices

_BUTTON_MAP = {"left": e.BTN_LEFT, "right": e.BTN_RIGHT, "middle": e.BTN_MIDDLE}


def _resolve_button(name: str) -> int:
    if name not in _BUTTON_MAP:
        raise ValueError(f"Unknown button: {name!r}. Use: left, right, middle")
    return _BUTTON_MAP[name]


def move_mouse(x: int, y: int) -> None:
    """Move mouse cursor to absolute screen coordinates.

    Args:
        x: Target X coordinate in screen pixels.
        y: Target Y coordinate in screen pixels.
    """
    devices.mouse.write(e.EV_ABS, e.ABS_X, x)
    devices.mouse.write(e.EV_ABS, e.ABS_Y, y)
    devices.mouse.syn()


def click(x: int, y: int, button: str = "left") -> None:
    """Move to coordinates and click.

    Args:
        x: Target X coordinate.
        y: Target Y coordinate.
        button: "left", "right", or "middle".
    """
    move_mouse(x, y)
    btn = _resolve_button(button)
    devices.mouse.write(e.EV_KEY, btn, 1)
    devices.mouse.syn()
    devices.mouse.write(e.EV_KEY, btn, 0)
    devices.mouse.syn()


def double_click(x: int, y: int) -> None:
    """Move to coordinates and double-click.

    Args:
        x: Target X coordinate.
        y: Target Y coordinate.
    """
    click(x, y)
    time.sleep(0.05)
    click(x, y)


def drag(from_x: int, from_y: int, to_x: int, to_y: int) -> None:
    """Click and drag from one position to another.

    Args:
        from_x: Drag start X.
        from_y: Drag start Y.
        to_x: Drag end X.
        to_y: Drag end Y.
    """
    move_mouse(from_x, from_y)
    devices.mouse.write(e.EV_KEY, e.BTN_LEFT, 1)
    devices.mouse.syn()
    steps = max(abs(to_x - from_x), abs(to_y - from_y)) // 10 or 1
    for i in range(1, steps + 1):
        ix = from_x + (to_x - from_x) * i // steps
        iy = from_y + (to_y - from_y) * i // steps
        move_mouse(ix, iy)
        time.sleep(0.005)
    devices.mouse.write(e.EV_KEY, e.BTN_LEFT, 0)
    devices.mouse.syn()


def scroll(x: int, y: int, direction: str, amount: int) -> None:
    """Scroll at coordinates.

    Args:
        x: X coordinate to scroll at.
        y: Y coordinate to scroll at.
        direction: "up" or "down".
        amount: Number of scroll ticks.
    """
    if direction not in ("up", "down"):
        raise ValueError(f"Unknown direction: {direction!r}. Must be 'up' or 'down'")
    move_mouse(x, y)
    value = 1 if direction == "up" else -1
    for _ in range(amount):
        devices.mouse.write(e.EV_REL, e.REL_WHEEL, value)
        devices.mouse.syn()
        time.sleep(0.02)
