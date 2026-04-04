"""Virtual input device manager — SPEC-002.

Creates two persistent UInput virtual devices at MCP server startup:
- "HyprAgent Keyboard" — full virtual keyboard
- "HyprAgent Mouse" — absolute pointer (EV_ABS, INPUT_PROP_DIRECT)

These devices appear to the kernel and Hyprland as separate physical hardware,
leaving the user's real input devices untouched during agent operation.
"""

from __future__ import annotations

try:
    from evdev import UInput, AbsInfo, ecodes as e
except ImportError as exc:
    raise ImportError(
        "python-evdev is required for virtual input devices.\n"
        "Install with: uv add evdev\n"
        "Also ensure /dev/uinput is writable: sudo usermod -aG input $USER"
    ) from exc

import logging

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Keyboard capabilities — all standard keys KEY_ESC through KEY_MICMUTE
# ---------------------------------------------------------------------------

KB_CAPABILITIES: dict = {
    e.EV_KEY: [
        *range(e.KEY_ESC, e.KEY_MICMUTE + 1),
        # Explicit modifiers (belt-and-suspenders)
        e.KEY_LEFTSHIFT,  e.KEY_RIGHTSHIFT,
        e.KEY_LEFTCTRL,   e.KEY_RIGHTCTRL,
        e.KEY_LEFTALT,    e.KEY_RIGHTALT,
        e.KEY_LEFTMETA,   e.KEY_RIGHTMETA,
    ]
}


def _build_mouse_capabilities(screen_w: int, screen_h: int) -> dict:
    """Build mouse capability dict for given screen resolution."""
    return {
        e.EV_KEY: [
            e.BTN_LEFT,
            e.BTN_RIGHT,
            e.BTN_MIDDLE,
        ],
        e.EV_ABS: [
            (e.ABS_X, AbsInfo(value=0, min=0, max=screen_w, fuzz=0, flat=0, resolution=0)),
            (e.ABS_Y, AbsInfo(value=0, min=0, max=screen_h, fuzz=0, flat=0, resolution=0)),
        ],
        e.EV_REL: [e.REL_WHEEL],
        e.EV_SYN: [e.SYN_REPORT],
    }


class DeviceManager:
    """Owns both virtual input devices for the lifetime of the MCP server process."""

    keyboard: UInput | None
    mouse: UInput | None
    _started: bool

    def __init__(self) -> None:
        self.keyboard = None
        self.mouse = None
        self._started = False

    def start(self, config: object | None = None) -> None:
        """Create both virtual devices. Call once at MCP server startup.

        Args:
            config: Project config object. If None, defaults to 2560×1440.
                    Reads config.tools.mouse.screen_width / screen_height.
        """
        if self._started:
            logger.warning("DeviceManager.start() called twice — ignoring")
            return

        # Read screen resolution from config or fall back to sensible defaults
        screen_w = 2560
        screen_h = 1440
        if config is not None:
            try:
                screen_w = config.tools.mouse.screen_width
                screen_h = config.tools.mouse.screen_height
            except AttributeError:
                logger.warning(
                    "config.tools.mouse.screen_width/height not found — "
                    "defaulting to %dx%d", screen_w, screen_h
                )

        self.keyboard = UInput(
            KB_CAPABILITIES,
            name="HyprAgent Keyboard",
            vendor=0x4841,    # ASCII "HA"
            product=0x4B42,   # ASCII "KB"
            version=0x0001,
        )

        self.mouse = UInput(
            _build_mouse_capabilities(screen_w, screen_h),
            name="HyprAgent Mouse",
            vendor=0x4841,    # ASCII "HA"
            product=0x4D53,   # ASCII "MS"
            version=0x0001,
            input_props=[e.INPUT_PROP_DIRECT],  # Required for Wayland ABS acceptance
        )

        self._started = True
        logger.info(
            "DeviceManager started — keyboard: %s, mouse: %s",
            self.keyboard.device.path,
            self.mouse.device.path,
        )
        print(
            f"[HyprAgent] Virtual devices created:\n"
            f"  Keyboard: {self.keyboard.device.path}\n"
            f"  Mouse:    {self.mouse.device.path}  ({screen_w}×{screen_h})"
        )

    def stop(self) -> None:
        """Destroy both virtual devices. Call at MCP server shutdown."""
        if not self._started:
            return
        if self.keyboard is not None:
            self.keyboard.close()
            self.keyboard = None
        if self.mouse is not None:
            self.mouse.close()
            self.mouse = None
        self._started = False
        logger.info("DeviceManager stopped — virtual devices destroyed")

    def verify(self) -> dict:
        """Return device info dict for status/health check."""
        if not self._started:
            return {"started": False, "keyboard": None, "mouse": None}
        return {
            "started": True,
            "keyboard": {
                "name": self.keyboard.name,
                "path": self.keyboard.device.path,
                "fd": self.keyboard.fd,
            },
            "mouse": {
                "name": self.mouse.name,
                "path": self.mouse.device.path,
                "fd": self.mouse.fd,
            },
        }


# Module-level singleton — import from here in tool modules
devices = DeviceManager()
