"""Hyprland/Wayland harness — grim + evdev + hyprctl + wl-clipboard + pytesseract.

Every platform-specific binary call lives here. Tool modules call harness methods.

Lazy imports: evdev, pytesseract, and PIL are imported inside methods so
non-Linux platforms don't break and optional deps are only required at runtime.
"""

from __future__ import annotations

import base64
import json
import logging
import os
import subprocess
import tempfile
import time
import uuid

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Module-level helpers (no instance state)
# ---------------------------------------------------------------------------

def _detect_layout() -> str:
    """Detect the system keyboard layout via localectl.

    Respects HYPRAGENT_KEYBOARD_LAYOUT env var override.
    Falls back to 'us' if detection fails.
    """
    override = os.environ.get("HYPRAGENT_KEYBOARD_LAYOUT")
    if override:
        return override.lower()

    try:
        result = subprocess.run(
            ["localectl", "status"],
            capture_output=True, text=True, timeout=5,
        )
        for line in result.stdout.splitlines():
            if "X11 Layout" in line:
                layout = line.split(":")[-1].strip()
                if layout:
                    return layout.lower()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    try:
        result = subprocess.run(
            ["setxkbmap", "-query"],
            capture_output=True, text=True, timeout=5,
        )
        for line in result.stdout.splitlines():
            if line.startswith("layout:"):
                layout = line.split(":")[-1].strip()
                if layout:
                    return layout.lower()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    return "us"


def _build_keymap(layout: str) -> dict[str, tuple[int, bool]]:
    """Build a keymap for the given XKB layout.

    Args:
        layout: XKB layout code (e.g. 'us', 'de', 'fr').

    Returns:
        Dict mapping character → (keycode, needs_shift).
    """
    if layout != "us":
        pass  # non-US layouts fall back to clipboard paste for unknown chars

    from evdev import ecodes as e

    return {
        "a": (e.KEY_A, False), "b": (e.KEY_B, False), "c": (e.KEY_C, False),
        "d": (e.KEY_D, False), "e": (e.KEY_E, False), "f": (e.KEY_F, False),
        "g": (e.KEY_G, False), "h": (e.KEY_H, False), "i": (e.KEY_I, False),
        "j": (e.KEY_J, False), "k": (e.KEY_K, False), "l": (e.KEY_L, False),
        "m": (e.KEY_M, False), "n": (e.KEY_N, False), "o": (e.KEY_O, False),
        "p": (e.KEY_P, False), "q": (e.KEY_Q, False), "r": (e.KEY_R, False),
        "s": (e.KEY_S, False), "t": (e.KEY_T, False), "u": (e.KEY_U, False),
        "v": (e.KEY_V, False), "w": (e.KEY_W, False), "x": (e.KEY_X, False),
        "y": (e.KEY_Y, False), "z": (e.KEY_Z, False),
        "A": (e.KEY_A, True), "B": (e.KEY_B, True), "C": (e.KEY_C, True),
        "D": (e.KEY_D, True), "E": (e.KEY_E, True), "F": (e.KEY_F, True),
        "G": (e.KEY_G, True), "H": (e.KEY_H, True), "I": (e.KEY_I, True),
        "J": (e.KEY_J, True), "K": (e.KEY_K, True), "L": (e.KEY_L, True),
        "M": (e.KEY_M, True), "N": (e.KEY_N, True), "O": (e.KEY_O, True),
        "P": (e.KEY_P, True), "Q": (e.KEY_Q, True), "R": (e.KEY_R, True),
        "S": (e.KEY_S, True), "T": (e.KEY_T, True), "U": (e.KEY_U, True),
        "V": (e.KEY_V, True), "W": (e.KEY_W, True), "X": (e.KEY_X, True),
        "Y": (e.KEY_Y, True), "Z": (e.KEY_Z, True),
        "0": (e.KEY_0, False), "1": (e.KEY_1, False), "2": (e.KEY_2, False),
        "3": (e.KEY_3, False), "4": (e.KEY_4, False), "5": (e.KEY_5, False),
        "6": (e.KEY_6, False), "7": (e.KEY_7, False), "8": (e.KEY_8, False),
        "9": (e.KEY_9, False),
        " ": (e.KEY_SPACE, False),
        "\n": (e.KEY_ENTER, False),
        "\t": (e.KEY_TAB, False),
        "`": (e.KEY_GRAVE, False),
        "-": (e.KEY_MINUS, False),
        "=": (e.KEY_EQUAL, False),
        "[": (e.KEY_LEFTBRACE, False),
        "]": (e.KEY_RIGHTBRACE, False),
        "\\": (e.KEY_BACKSLASH, False),
        ";": (e.KEY_SEMICOLON, False),
        "'": (e.KEY_APOSTROPHE, False),
        ",": (e.KEY_COMMA, False),
        ".": (e.KEY_DOT, False),
        "/": (e.KEY_SLASH, False),
        "!": (e.KEY_1, True),
        "@": (e.KEY_2, True),
        "#": (e.KEY_3, True),
        "$": (e.KEY_4, True),
        "%": (e.KEY_5, True),
        "^": (e.KEY_6, True),
        "&": (e.KEY_7, True),
        "*": (e.KEY_8, True),
        "(": (e.KEY_9, True),
        ")": (e.KEY_0, True),
        "_": (e.KEY_MINUS, True),
        "+": (e.KEY_EQUAL, True),
        "{": (e.KEY_LEFTBRACE, True),
        "}": (e.KEY_RIGHTBRACE, True),
        "|": (e.KEY_BACKSLASH, True),
        ":": (e.KEY_SEMICOLON, True),
        '"': (e.KEY_APOSTROPHE, True),
        "<": (e.KEY_COMMA, True),
        ">": (e.KEY_DOT, True),
        "?": (e.KEY_SLASH, True),
        "~": (e.KEY_GRAVE, True),
    }


_MODIFIER_MAP: dict[str, int] = {}

_BUTTON_MAP: dict[str, int] = {}


def _ensure_evdev_maps() -> None:
    """Lazily populate modifier and button maps from evdev ecodes."""
    if _MODIFIER_MAP:
        return
    from evdev import ecodes as e

    _MODIFIER_MAP.update({
        "ctrl": e.KEY_LEFTCTRL,
        "shift": e.KEY_LEFTSHIFT,
        "alt": e.KEY_LEFTALT,
        "super": e.KEY_LEFTMETA,
        "meta": e.KEY_LEFTMETA,
    })
    _BUTTON_MAP.update({
        "left": e.BTN_LEFT,
        "right": e.BTN_RIGHT,
        "middle": e.BTN_MIDDLE,
    })


# ---------------------------------------------------------------------------
# UInput capabilities — keyboard
# ---------------------------------------------------------------------------

def _kb_capabilities() -> dict:
    from evdev import ecodes as e

    return {
        e.EV_KEY: [
            *range(e.KEY_ESC, e.KEY_MICMUTE + 1),
            e.KEY_LEFTSHIFT, e.KEY_RIGHTSHIFT,
            e.KEY_LEFTCTRL, e.KEY_RIGHTCTRL,
            e.KEY_LEFTALT, e.KEY_RIGHTALT,
            e.KEY_LEFTMETA, e.KEY_RIGHTMETA,
        ]
    }


def _build_mouse_capabilities(screen_w: int, screen_h: int) -> dict:
    from evdev import AbsInfo, ecodes as e

    return {
        e.EV_KEY: [e.BTN_LEFT, e.BTN_RIGHT, e.BTN_MIDDLE],
        e.EV_ABS: [
            (e.ABS_X, AbsInfo(value=0, min=0, max=screen_w, fuzz=0, flat=0, resolution=0)),
            (e.ABS_Y, AbsInfo(value=0, min=0, max=screen_h, fuzz=0, flat=0, resolution=0)),
        ],
        e.EV_REL: [e.REL_WHEEL],
    }


# ---------------------------------------------------------------------------
# HyprlandHarness
# ---------------------------------------------------------------------------

class HyprlandHarness:
    """Harness for Hyprland/Wayland using grim, evdev, hyprctl, and wl-clipboard."""

    name = "hyprland"

    def __init__(self) -> None:
        self.keyboard = None
        self.mouse = None
        self._started = False
        self._keymap: dict[str, tuple[int, bool]] = {}
        self._screen_w = 2560
        self._screen_h = 1440

    # ── Lifecycle ──────────────────────────────────────────────────────────────

    def start(self, config: object | None = None) -> None:
        """Initialize UInput devices and detect screen resolution.

        Idempotent — safe to call multiple times.

        Args:
            config: Optional config object with tools.mouse.screen_width/height.
        """
        if self._started:
            return

        self._detect_screen_resolution()

        # Override resolution from config if provided
        if config is not None:
            try:
                self._screen_w = config["tools"]["mouse"]["screen_width"]
                self._screen_h = config["tools"]["mouse"]["screen_height"]
            except (KeyError, TypeError):
                pass

        self._create_devices()
        self._keymap = _build_keymap(_detect_layout())
        _ensure_evdev_maps()
        self._started = True
        logger.info(
            "HyprlandHarness started — keyboard: %s, mouse: %s",
            self.keyboard.device.path if self.keyboard else "?",
            self.mouse.device.path if self.mouse else "?",
        )

    def stop(self) -> None:
        """Destroy UInput devices. Idempotent."""
        if not self._started:
            return
        if self.keyboard is not None:
            self.keyboard.close()
            self.keyboard = None
        if self.mouse is not None:
            self.mouse.close()
            self.mouse = None
        self._started = False
        logger.info("HyprlandHarness stopped — virtual devices destroyed")

    def verify(self) -> dict:
        """Return diagnostic info about harness health."""
        if not self._started:
            return {"name": self.name, "started": False}
        return {
            "name": self.name,
            "started": True,
            "keyboard": {
                "name": self.keyboard.name if self.keyboard else None,
                "path": self.keyboard.device.path if self.keyboard else None,
                "fd": self.keyboard.fd if self.keyboard else None,
            },
            "mouse": {
                "name": self.mouse.name if self.mouse else None,
                "path": self.mouse.device.path if self.mouse else None,
                "fd": self.mouse.fd if self.mouse else None,
            },
            "resolution": f"{self._screen_w}x{self._screen_h}",
        }

    # ── Device creation ────────────────────────────────────────────────────────

    def _detect_screen_resolution(self) -> None:
        """Auto-detect screen resolution from hyprctl monitors."""
        try:
            result = subprocess.run(
                ["hyprctl", "monitors", "-j"],
                capture_output=True, text=True, timeout=5,
            )
            if result.returncode == 0 and result.stdout.strip():
                monitors = json.loads(result.stdout)
                if monitors:
                    # Find the focused monitor (the one Hyprland is currently using)
                    focused = None
                    for m in monitors:
                        if m.get("focused", False):
                            focused = m
                            break
                    if focused is None:
                        focused = monitors[0]  # fallback to first if none focused
                    scale = focused.get("scale", 1.0) or 1.0
                    self._screen_w = int(focused.get("width", self._screen_w) / scale)
                    self._screen_h = int(focused.get("height", self._screen_h) / scale)
        except (subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError):
            pass

    def _create_devices(self) -> None:
        from evdev import UInput, ecodes as e

        # Keyboard
        self.keyboard = UInput(
            _kb_capabilities(),
            name="HyprAgent Keyboard",
            vendor=0x4841,
            product=0x4B42,
            version=0x0001,
        )

        # Mouse — try INPUT_PROP_DIRECT first, fall back to POINTER, then no props
        mouse_caps = _build_mouse_capabilities(self._screen_w, self._screen_h)
        mouse_base = dict(
            name="HyprAgent Mouse",
            vendor=0x4841,
            product=0x4D53,
            version=0x0001,
        )
        _prop_variants: list = [
            [e.INPUT_PROP_DIRECT],
            [e.INPUT_PROP_POINTER],
            None,
        ]
        for props in _prop_variants:
            try:
                kw = {**mouse_base}
                if props is not None:
                    kw["input_props"] = props
                self.mouse = UInput(mouse_caps, **kw)
                logger.info("Mouse created with input_props=%s", props)
                break
            except OSError as exc:
                if exc.errno != 22:
                    raise
                logger.warning(
                    "Mouse creation rejected input_props=%s (EINVAL) — trying next variant",
                    props,
                )
        else:
            raise RuntimeError(
                "Failed to create HyprAgent Mouse — kernel rejected all input_props variants.\n"
                "Ensure uinput module is loaded: sudo modprobe uinput"
            )

        print(
            f"[HyprAgent] Virtual devices created:\n"
            f"  Keyboard: {self.keyboard.device.path}\n"
            f"  Mouse:    {self.mouse.device.path}  ({self._screen_w}x{self._screen_h})"
        )

    # ── Screenshot (grim) ──────────────────────────────────────────────────────

    def _grim(self, *grim_args: str) -> str:
        """Run grim with output to stdout and return base64-encoded PNG.

        Args:
            *grim_args: Additional arguments inserted before the output path ("-").

        Returns:
            Base64-encoded PNG string.

        Raises:
            RuntimeError: If grim exits non-zero.
        """
        result = subprocess.run(
            ["grim", *grim_args, "-"],
            capture_output=True,
        )
        if result.returncode != 0:
            raise RuntimeError(f"grim failed: {result.stderr.decode().strip()}")
        return base64.b64encode(result.stdout).decode("ascii")

    def capture_fullscreen(self) -> str:
        """Capture the entire screen → base64 PNG."""
        return self._grim()

    def capture_region(self, x: int, y: int, width: int, height: int) -> str:
        """Capture a screen region → base64 PNG."""
        if width <= 0 or height <= 0:
            raise ValueError(f"width and height must be > 0, got {width}x{height}")
        return self._grim("-g", f"{x},{y} {width}x{height}")

    def capture_window(self) -> str:
        """Capture only the active window -> base64 PNG.

        Uses hyprctl activewindow -j for geometry, then grim -g to capture.
        """
        try:
            result = subprocess.run(
                ["hyprctl", "activewindow", "-j"],
                capture_output=True, text=True, timeout=5,
            )
            if result.returncode != 0:
                raise RuntimeError(f"hyprctl activewindow failed: {result.stderr.strip()}")
            win = json.loads(result.stdout)
        except json.JSONDecodeError:
            raise RuntimeError("Failed to parse hyprctl activewindow output")
        if not win or not win.get("address"):
            raise RuntimeError("No active window to capture")
        at = win.get("at", [0, 0])
        size = win.get("size", [0, 0])
        x, y = at[0], at[1]
        w, h = size[0], size[1]
        if w <= 0 or h <= 0:
            raise RuntimeError(f"Invalid window geometry: {w}x{h}")
        return self._grim("-g", f"{x},{y} {w}x{h}")

    def save_screenshot(self, path: str) -> None:
        """Capture fullscreen and save to file."""
        result = subprocess.run(
            ["grim", path],
            capture_output=True,
        )
        if result.returncode != 0:
            raise RuntimeError(f"grim failed: {result.stderr.decode().strip()}")

    # ── Mouse (evdev) ──────────────────────────────────────────────────────────

    def move_mouse(self, x: int, y: int) -> None:
        from evdev import ecodes as e

        self.mouse.write(e.EV_ABS, e.ABS_X, x)
        self.mouse.write(e.EV_ABS, e.ABS_Y, y)
        self.mouse.syn()

    def click(self, x: int, y: int, button: str = "left") -> None:
        from evdev import ecodes as e

        self.move_mouse(x, y)
        btn = _BUTTON_MAP[button]
        self.mouse.write(e.EV_KEY, btn, 1)
        self.mouse.syn()
        self.mouse.write(e.EV_KEY, btn, 0)
        self.mouse.syn()

    def double_click(self, x: int, y: int) -> None:
        self.click(x, y)
        time.sleep(0.05)
        self.click(x, y)

    def drag(self, from_x: int, from_y: int, to_x: int, to_y: int) -> None:
        from evdev import ecodes as e

        self.move_mouse(from_x, from_y)
        self.mouse.write(e.EV_KEY, e.BTN_LEFT, 1)
        self.mouse.syn()
        steps = max(abs(to_x - from_x), abs(to_y - from_y)) // 10 or 1
        for i in range(1, steps + 1):
            ix = from_x + (to_x - from_x) * i // steps
            iy = from_y + (to_y - from_y) * i // steps
            self.move_mouse(ix, iy)
            time.sleep(0.005)
        self.mouse.write(e.EV_KEY, e.BTN_LEFT, 0)
        self.mouse.syn()

    def scroll(self, x: int, y: int, direction: str, amount: int = 3) -> None:
        from evdev import ecodes as e

        if direction not in ("up", "down"):
            raise ValueError(f"Unknown direction: {direction!r}. Must be 'up' or 'down'")
        self.move_mouse(x, y)
        value = 1 if direction == "up" else -1
        for _ in range(amount):
            self.mouse.write(e.EV_REL, e.REL_WHEEL, value)
            self.mouse.syn()
            time.sleep(0.02)

    # ── Keyboard (evdev) ──────────────────────────────────────────────────────

    def _press_key_raw(self, keycode: int, hold: bool | None = None) -> None:
        from evdev import ecodes as e

        if hold is True:
            self.keyboard.write(e.EV_KEY, keycode, 1)
            self.keyboard.syn()
        elif hold is False:
            self.keyboard.write(e.EV_KEY, keycode, 0)
            self.keyboard.syn()
        else:
            self.keyboard.write(e.EV_KEY, keycode, 1)
            self.keyboard.syn()
            self.keyboard.write(e.EV_KEY, keycode, 0)
            self.keyboard.syn()

    def _paste_via_clipboard(self, text: str) -> None:
        """Paste text via wl-copy + simulated paste keystroke."""
        subprocess.run(["wl-copy", text], check=True)
        time.sleep(0.02)
        self.press_key("ctrl+v")
        time.sleep(0.02)

    def _resolve_modifier(self, name: str) -> int:
        _ensure_evdev_maps()
        if name not in _MODIFIER_MAP:
            raise ValueError(f"Unknown modifier: {name!r}")
        return _MODIFIER_MAP[name]

    def _resolve_key(self, name: str) -> int:
        from evdev import ecodes as e

        code = getattr(e, f"KEY_{name.upper()}", None)
        if code is not None:
            return code
        if name.startswith("f") and name[1:].isdigit():
            code = getattr(e, f"KEY_F{name[1:]}", None)
            if code is not None:
                return code
        # Fallback: check keymap for printable characters like '/'
        entry = self._keymap.get(name)
        if entry is not None:
            return entry[0]  # just the keycode (caller handles modifiers)
        raise ValueError(f"Unknown key: {name!r}")

    def type_text(self, text: str) -> None:
        from evdev import ecodes as e

        if not text:
            raise ValueError("text must not be empty")
        for char in text:
            entry = self._keymap.get(char)
            if entry is None:
                self._paste_via_clipboard(char)
                continue
            keycode, needs_shift = entry
            if needs_shift:
                self._press_key_raw(e.KEY_LEFTSHIFT, hold=True)
            self._press_key_raw(keycode)
            if needs_shift:
                self._press_key_raw(e.KEY_LEFTSHIFT, hold=False)
            time.sleep(0.012)

    def press_key(self, key: str) -> None:
        from evdev import ecodes as e

        # Detect single printable character — delegate to type_text for proper shift handling
        if len(key) == 1 and "+" not in key:
            self.type_text(key)
            return

        parts = [p.strip().lower() for p in key.split("+")]
        modifiers, main_key = parts[:-1], parts[-1]
        mod_codes = [self._resolve_modifier(m) for m in modifiers]
        key_code = self._resolve_key(main_key)
        for mod in mod_codes:
            self.keyboard.write(e.EV_KEY, mod, 1)
        self.keyboard.write(e.EV_KEY, key_code, 1)
        self.keyboard.syn()
        self.keyboard.write(e.EV_KEY, key_code, 0)
        for mod in reversed(mod_codes):
            self.keyboard.write(e.EV_KEY, mod, 0)
        self.keyboard.syn()

    def hotkey(self, *keys: str) -> None:
        if not keys:
            raise ValueError("at least one key required")
        self.press_key("+".join(keys))

    # ── OCR (pytesseract) ─────────────────────────────────────────────────────

    def extract_text_from_image(self, image_path: str) -> str:
        """Extract text from an image file using Tesseract OCR."""
        from PIL import Image
        import pytesseract
        img = Image.open(image_path)
        return pytesseract.image_to_string(img)

    def extract_text_fullscreen(self) -> str:
        """Capture full screen and extract all visible text."""
        from PIL import Image
        import pytesseract
        path = os.path.join(tempfile.gettempdir(), f"hypr-ocr-{uuid.uuid4()}.png")
        try:
            result = subprocess.run(["grim", path], capture_output=True, text=True)
            if result.returncode != 0:
                raise RuntimeError(f"grim failed: {result.stderr.strip()}")
            return pytesseract.image_to_string(Image.open(path))
        finally:
            if os.path.exists(path):
                os.remove(path)

    def extract_text_from_region(self, x: int, y: int, width: int, height: int) -> str:
        """Capture a screen region and extract text from it."""
        from PIL import Image
        import pytesseract
        if width <= 0 or height <= 0:
            raise ValueError(f"width and height must be > 0, got {width}x{height}")
        path = os.path.join(tempfile.gettempdir(), f"hypr-ocr-{uuid.uuid4()}.png")
        try:
            result = subprocess.run(
                ["grim", "-g", f"{x},{y} {width}x{height}", path],
                capture_output=True, text=True,
            )
            if result.returncode != 0:
                raise RuntimeError(f"grim failed: {result.stderr.strip()}")
            return pytesseract.image_to_string(Image.open(path))
        finally:
            if os.path.exists(path):
                os.remove(path)

    def extract_active_window_text(self) -> str:
        """Capture the active window and extract text from it via OCR."""
        from PIL import Image
        import pytesseract
        path = os.path.join(tempfile.gettempdir(), f"hypr-ocr-{uuid.uuid4()}.png")
        try:
            result = subprocess.run(
                ["hyprctl", "activewindow", "-j"],
                capture_output=True, text=True, timeout=5,
            )
            if result.returncode != 0:
                raise RuntimeError(f"hyprctl activewindow failed: {result.stderr.strip()}")
            win = json.loads(result.stdout)
            if not win or not win.get("address"):
                raise RuntimeError("No active window to capture")
            at = win.get("at", [0, 0])
            size = win.get("size", [0, 0])
            x, y = at[0], at[1]
            w, h = size[0], size[1]
            if w <= 0 or h <= 0:
                raise RuntimeError(f"Invalid window geometry: {w}x{h}")
            subprocess.run(
                ["grim", "-g", f"{x},{y} {w}x{h}", path],
                capture_output=True, check=True,
            )
            return pytesseract.image_to_string(Image.open(path))
        finally:
            if os.path.exists(path):
                os.remove(path)

    # ── Compositor / hyprctl ──────────────────────────────────────────────────

    def _check_hyprland(self) -> None:
        if not os.environ.get("HYPRLAND_INSTANCE_SIGNATURE"):
            raise RuntimeError(
                "Not running under Hyprland "
                "(HYPRLAND_INSTANCE_SIGNATURE not set)"
            )

    def _hyprctl(self, *args: str) -> str:
        """Run hyprctl with given args and return stdout."""
        self._check_hyprland()
        try:
            result = subprocess.run(
                ["hyprctl", *args],
                capture_output=True,
                text=True,
            )
        except FileNotFoundError:
            raise RuntimeError("hyprctl not found — is hyprland installed?")
        if result.returncode != 0:
            raise RuntimeError(f"hyprctl failed: {result.stderr.strip()}")
        return result.stdout

    def workspace_list(self) -> list[dict]:
        raw = json.loads(self._hyprctl("workspaces", "-j"))
        active_raw = json.loads(self._hyprctl("activeworkspace", "-j"))
        active_id = active_raw.get("id")
        return [
            {
                "id": ws["id"],
                "name": ws["name"],
                "windows": ws.get("windows", 0),
                "monitor": ws.get("monitor", ""),
                "active": ws["id"] == active_id,
            }
            for ws in raw
        ]

    def workspace_switch(self, target: str | int) -> None:
        self._hyprctl("dispatch", "workspace", str(target))

    def clients(self) -> list[dict]:
        raw = json.loads(self._hyprctl("clients", "-j"))
        return [
            {
                "address": c.get("address", ""),
                "class_": c.get("class", ""),
                "title": c.get("title", ""),
                "pid": c.get("pid", 0),
                "workspace_id": c.get("workspace", {}).get("id", 0),
                "workspace_name": c.get("workspace", {}).get("name", ""),
                "x": c.get("at", [0, 0])[0],
                "y": c.get("at", [0, 0])[1],
                "width": c.get("size", [0, 0])[0],
                "height": c.get("size", [0, 0])[1],
                "floating": bool(c.get("floating", False)),
                "fullscreen": bool(c.get("fullscreen", False)),
            }
            for c in raw
        ]

    def active_window(self) -> dict | None:
        raw = json.loads(self._hyprctl("activewindow", "-j"))
        if not raw or raw.get("message") == "Invalid" or not raw.get("address"):
            return None
        return {
            "address": raw.get("address", ""),
            "class_": raw.get("class", ""),
            "title": raw.get("title", ""),
            "workspace_id": raw.get("workspace", {}).get("id", 0),
            "workspace_name": raw.get("workspace", {}).get("name", ""),
        }

    def focus_window(self, target: str) -> None:
        # If target looks like a window title (contains spaces or long text),
        # try title-based matching first, then fall back to class matching.
        if " " in target or len(target) > 20:
            try:
                self._hyprctl("dispatch", "focuswindow", f"title:{target}")
                return
            except RuntimeError:
                pass  # Fall through to class matching
        if ":" not in target:
            target = f"class:{target}"
        self._hyprctl("dispatch", "focuswindow", target)

    def focus_window_by_title(self, title_substring: str) -> None:
        """Focus a window by partial title match.

        Searches all clients for a title containing the substring
        and focuses by address.
        """
        for client in self.clients():
            if title_substring.lower() in client["title"].lower():
                self._hyprctl("dispatch", "focuswindow", f"address:{client['address']}")
                return
        raise RuntimeError(f"No window with title containing {title_substring!r}")

    def launch_app(self, name: str) -> None:
        """Launch an app via hyprctl dispatch exec."""
        self._hyprctl("dispatch", "exec", name)

    def screen_resolution(self) -> tuple[int, int]:
        return (self._screen_w, self._screen_h)
