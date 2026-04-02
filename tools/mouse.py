"""Mouse control tool — Milestone M2.

System dependency: ydotool + ydotoold daemon (pacman -S ydotool)
Requires: uinput kernel module (modprobe uinput), user in input group.
"""

import os
import socket
import struct
import subprocess
import time

YDOTOOL_SOCKET = "/run/user/1000/.ydotool_socket"

_BUTTON_CODES = {
    "left": "0xC0",
    "right": "0xC1",
    "middle": "0xC2",
}


def _ydotool(*args: str) -> None:
    env = {**os.environ, "YDOTOOL_SOCKET": YDOTOOL_SOCKET}
    result = subprocess.run(["ydotool", *args], capture_output=True, text=True, env=env)
    if result.returncode != 0:
        raise RuntimeError(f"ydotool {args[0]} failed: {result.stderr.strip()}")


def move_mouse(x: int, y: int) -> None:
    """Move mouse cursor to absolute screen coordinates.

    Args:
        x: Target X coordinate in screen pixels.
        y: Target Y coordinate in screen pixels.
    """
    _ydotool("mousemove", "--absolute", "-x", str(x), "-y", str(y))


def click(x: int, y: int, button: str = "left") -> None:
    """Move to coordinates and click.

    Args:
        x: Target X coordinate.
        y: Target Y coordinate.
        button: "left", "right", or "middle".
    """
    code = _BUTTON_CODES.get(button)
    if code is None:
        raise ValueError(f"Unknown button: {button!r}. Must be one of {list(_BUTTON_CODES)}")
    _ydotool("mousemove", "--absolute", "-x", str(x), "-y", str(y))
    _ydotool("click", code)


def double_click(x: int, y: int) -> None:
    """Move to coordinates and double-click.

    Args:
        x: Target X coordinate.
        y: Target Y coordinate.
    """
    _ydotool("mousemove", "--absolute", "-x", str(x), "-y", str(y))
    _ydotool("click", "0xC0")
    time.sleep(0.05)
    _ydotool("click", "0xC0")


def drag(from_x: int, from_y: int, to_x: int, to_y: int) -> None:
    """Click and drag from one position to another.

    Args:
        from_x: Drag start X.
        from_y: Drag start Y.
        to_x: Drag end X.
        to_y: Drag end Y.
    """
    _ydotool("mousemove", "--absolute", "-x", str(from_x), "-y", str(from_y))
    _ydotool("click", "0x40")  # button down, no release
    _ydotool("mousemove", "--absolute", "-x", str(to_x), "-y", str(to_y))
    _ydotool("click", "0x80")  # button up, no press


def scroll(x: int, y: int, direction: str, amount: int) -> None:
    """Scroll at coordinates.

    ydotool 1.0.x has no scroll subcommand; inject REL_WHEEL events directly
    via the ydotoold Unix datagram socket.

    Args:
        x: X coordinate to scroll at.
        y: Y coordinate to scroll at.
        direction: "up" or "down".
        amount: Number of scroll ticks.
    """
    if direction not in ("up", "down"):
        raise ValueError(f"Unknown direction: {direction!r}. Must be 'up' or 'down'")
    _ydotool("mousemove", "--absolute", "-x", str(x), "-y", str(y))

    # Linux input_event: timeval(sec, usec) + type + code + value (24 bytes on 64-bit)
    _EV_SYN, _EV_REL = 0, 2
    _SYN_REPORT, _REL_WHEEL = 0, 8
    wheel_value = 1 if direction == "up" else -1

    def _event(t: int, c: int, v: int) -> bytes:
        ts = time.time()
        sec = int(ts)
        usec = int((ts - sec) * 1_000_000)
        return struct.pack("qqHHi", sec, usec, t, c, v)

    sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    try:
        for _ in range(amount):
            sock.sendto(_event(_EV_REL, _REL_WHEEL, wheel_value), YDOTOOL_SOCKET)
            sock.sendto(_event(_EV_SYN, _SYN_REPORT, 0), YDOTOOL_SOCKET)
    finally:
        sock.close()
