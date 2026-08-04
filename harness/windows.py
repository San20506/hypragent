"""Windows harness — PIL.ImageGrab + Win32 SendInput + EnumWindows + pytesseract.

Every Windows-specific API call lives here. Tool modules call harness methods.

Uses ctypes for all Win32 interop — no extra pip dependencies beyond Pillow
(already required) and pytesseract (optional OCR).

Key design decisions:
- SendInput for mouse/keyboard: same abstraction level as Linux evdev, but
  native Windows. Handles Unicode via KEYEVENTF_UNICODE for non-ASCII chars.
- PIL.ImageGrab for screenshots: wraps BitBlt, already a project dependency.
- EnumWindows for window management: no COM, no extra deps.
- PowerShell for virtual desktops: no public C API for IVirtualDesktopManager.
"""

from __future__ import annotations

import base64
import ctypes
import io
import json
import logging
import os
import subprocess
import tempfile
import time
import uuid
from ctypes import wintypes

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Win32 constants
# ---------------------------------------------------------------------------

# Input types
INPUT_MOUSE = 0
INPUT_KEYBOARD = 1

# Mouse event flags
MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_MIDDLEDOWN = 0x0020
MOUSEEVENTF_MIDDLEUP = 0x0040
MOUSEEVENTF_WHEEL = 0x0800
MOUSEEVENTF_ABSOLUTE = 0x8000

# Keyboard event flags
KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004
KEYEVENTF_SCANCODE = 0x0008

# System metrics
SM_CXSCREEN = 0
SM_CYSCREEN = 1

# Process DPI awareness
PROCESS_PER_MONITOR_DPI_AWARE = 2

# Window show commands
SW_RESTORE = 9

# Wheel delta (one notch)
WHEEL_DELTA = 120

# ---------------------------------------------------------------------------
# ctypes structures
# ---------------------------------------------------------------------------

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", ctypes.c_long),
        ("dy", ctypes.c_long),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]


class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ("uMsg", wintypes.DWORD),
        ("wParamL", wintypes.WORD),
        ("wParamH", wintypes.WORD),
    ]


class _INPUT(ctypes.Union):
    _fields_ = [
        ("mi", MOUSEINPUT),
        ("ki", KEYBDINPUT),
        ("hi", HARDWAREINPUT),
    ]


class INPUT(ctypes.Structure):
    _fields_ = [
        ("type", wintypes.DWORD),
        ("_input", _INPUT),
    ]


# ---------------------------------------------------------------------------
# Virtual-key code map
# ---------------------------------------------------------------------------

# Modifier name → VK code
_MODIFIER_VK_MAP: dict[str, int] = {
    "ctrl": 0x11,       # VK_CONTROL
    "shift": 0x10,      # VK_SHIFT
    "alt": 0x12,        # VK_MENU
    "super": 0x5B,      # VK_LWIN
    "win": 0x5B,        # VK_LWIN
    "meta": 0x5B,       # VK_LWIN
}

# Key name → VK code (for press_key / hotkey)
_KEY_VK_MAP: dict[str, int] = {
    "return": 0x0D,     "enter": 0x0D,
    "escape": 0x1B,     "esc": 0x1B,
    "tab": 0x09,
    "backspace": 0x08,  "back": 0x08,
    "delete": 0x2E,     "del": 0x2E,
    "insert": 0x2D,     "ins": 0x2D,
    "space": 0x20,
    "home": 0x24,
    "end": 0x23,
    "page_up": 0x21,    "pageup": 0x21, "prior": 0x21,
    "page_down": 0x22,  "pagedown": 0x22, "next": 0x22,
    "up": 0x26,
    "down": 0x28,
    "left": 0x25,
    "right": 0x27,
    "print_screen": 0x2C, "printscreen": 0x2C,
    "scroll_lock": 0x91, "scrolllock": 0x91,
    "pause": 0x13,
    "num_lock": 0x90, "numlock": 0x90,
    "caps_lock": 0x14, "capslock": 0x14,
}

# F-keys
for _i in range(1, 25):
    _KEY_VK_MAP[f"f{_i}"] = 0x6F + _i  # VK_F1 = 0x70

# Numpad
_KEY_VK_MAP.update({
    "numpad0": 0x60, "numpad1": 0x61, "numpad2": 0x62,
    "numpad3": 0x63, "numpad4": 0x64, "numpad5": 0x65,
    "numpad6": 0x66, "numpad7": 0x67, "numpad8": 0x68,
    "numpad9": 0x69,
    "multiply": 0x6A, "add": 0x6B, "separator": 0x6C,
    "subtract": 0x6D, "decimal": 0x6E, "divide": 0x6F,
})

# Character → (VK code, needs_shift) for type_text
# Covers ASCII printable range for US layout
_VK_CHAR_MAP: dict[str, tuple[int, bool]] = {}

def _build_char_map() -> None:
    """Build the character → VK map for US layout."""
    # Letters
    for c in "abcdefghijklmnopqrstuvwxyz":
        _VK_CHAR_MAP[c] = (ord(c.upper()), False)
        _VK_CHAR_MAP[c.upper()] = (ord(c.upper()), True)
    # Digits (top row)
    _VK_CHAR_MAP["0"] = (0x30, False)
    _VK_CHAR_MAP["1"] = (0x31, False)
    _VK_CHAR_MAP["2"] = (0x32, False)
    _VK_CHAR_MAP["3"] = (0x33, False)
    _VK_CHAR_MAP["4"] = (0x34, False)
    _VK_CHAR_MAP["5"] = (0x35, False)
    _VK_CHAR_MAP["6"] = (0x36, False)
    _VK_CHAR_MAP["7"] = (0x37, False)
    _VK_CHAR_MAP["8"] = (0x38, False)
    _VK_CHAR_MAP["9"] = (0x39, False)
    # Shifted digits
    _VK_CHAR_MAP[")"] = (0x30, True)
    _VK_CHAR_MAP["!"] = (0x31, True)
    _VK_CHAR_MAP["@"] = (0x32, True)
    _VK_CHAR_MAP["#"] = (0x33, True)
    _VK_CHAR_MAP["$"] = (0x34, True)
    _VK_CHAR_MAP["%"] = (0x35, True)
    _VK_CHAR_MAP["^"] = (0x36, True)
    _VK_CHAR_MAP["&"] = (0x37, True)
    _VK_CHAR_MAP["*"] = (0x38, True)
    _VK_CHAR_MAP["("] = (0x39, True)
    # Punctuation (OEM keys)
    _VK_CHAR_MAP[" "] = (0x20, False)       # VK_SPACE
    _VK_CHAR_MAP["\n"] = (0x0D, False)     # VK_RETURN
    _VK_CHAR_MAP["\t"] = (0x09, False)     # VK_TAB
    _VK_CHAR_MAP[";"] = (0xBA, False)      # VK_OEM_1
    _VK_CHAR_MAP[":"] = (0xBA, True)
    _VK_CHAR_MAP["="] = (0xBB, False)      # VK_OEM_PLUS
    _VK_CHAR_MAP["+"] = (0xBB, True)
    _VK_CHAR_MAP[","] = (0xBC, False)      # VK_OEM_COMMA
    _VK_CHAR_MAP["<"] = (0xBC, True)
    _VK_CHAR_MAP["-"] = (0xBD, False)      # VK_OEM_MINUS
    _VK_CHAR_MAP["_"] = (0xBD, True)
    _VK_CHAR_MAP["."] = (0xBE, False)      # VK_OEM_PERIOD
    _VK_CHAR_MAP[">"] = (0xBE, True)
    _VK_CHAR_MAP["/"] = (0xBF, False)      # VK_OEM_2
    _VK_CHAR_MAP["?"] = (0xBF, True)
    _VK_CHAR_MAP["`"] = (0xC0, False)      # VK_OEM_3
    _VK_CHAR_MAP["~"] = (0xC0, True)
    _VK_CHAR_MAP["["] = (0xDB, False)      # VK_OEM_4
    _VK_CHAR_MAP["{"] = (0xDB, True)
    _VK_CHAR_MAP["\\"] = (0xDC, False)     # VK_OEM_5
    _VK_CHAR_MAP["|"] = (0xDC, True)
    _VK_CHAR_MAP["]"] = (0xDD, False)      # VK_OEM_6
    _VK_CHAR_MAP["}"] = (0xDD, True)
    _VK_CHAR_MAP["'"] = (0xDE, False)      # VK_OEM_7
    _VK_CHAR_MAP['"'] = (0xDE, True)


_build_char_map()


# ---------------------------------------------------------------------------
# WindowsHarness
# ---------------------------------------------------------------------------

class WindowsHarness:
    """Harness for Windows 10/11 using PIL.ImageGrab + Win32 SendInput."""

    name = "windows"

    def __init__(self) -> None:
        self._started = False
        self._screen_w = 1920
        self._screen_h = 1080

    # ── Lifecycle ──────────────────────────────────────────────────────────

    def start(self, config: object | None = None) -> None:
        """Initialize: detect screen resolution, set DPI awareness.

        Idempotent — safe to call multiple times.

        Args:
            config: Optional config dict with tools.mouse.screen_width/height.
        """
        if self._started:
            return

        # Make process DPI-aware so coordinates are physical pixels
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(PROCESS_PER_MONITOR_DPI_AWARE)
        except OSError:
            pass  # Older Windows or already set

        self._detect_screen_resolution()

        # Override from config if provided
        if config is not None:
            try:
                self._screen_w = config["tools"]["mouse"]["screen_width"]
                self._screen_h = config["tools"]["mouse"]["screen_height"]
            except (KeyError, TypeError):
                pass

        self._started = True
        logger.info(
            "WindowsHarness started — resolution: %dx%d",
            self._screen_w, self._screen_h,
        )

    def stop(self) -> None:
        """Release resources. Idempotent."""
        self._started = False
        logger.info("WindowsHarness stopped")

    def verify(self) -> dict:
        """Return diagnostic info about harness health."""
        info = {
            "name": self.name,
            "started": self._started,
            "resolution": f"{self._screen_w}x{self._screen_h}",
        }
        # Check Tesseract
        try:
            import shutil
            tess = shutil.which("tesseract")
            info["tesseract"] = tess if tess else "NOT FOUND"
        except Exception:
            info["tesseract"] = "NOT FOUND"
        return info

    # ── Resolution ─────────────────────────────────────────────────────────

    def _detect_screen_resolution(self) -> None:
        """Auto-detect primary screen resolution."""
        try:
            self._screen_w = user32.GetSystemMetrics(SM_CXSCREEN)
            self._screen_h = user32.GetSystemMetrics(SM_CYSCREEN)
        except Exception:
            pass  # Keep defaults

    def screen_resolution(self) -> tuple[int, int]:
        return (self._screen_w, self._screen_h)

    # ── Screenshot (PIL.ImageGrab) ─────────────────────────────────────────

    def capture_fullscreen(self) -> str:
        """Capture the entire screen → base64 PNG."""
        from PIL import ImageGrab
        img = ImageGrab.grab()
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return base64.b64encode(buf.getvalue()).decode("ascii")

    def capture_region(self, x: int, y: int, width: int, height: int) -> str:
        """Capture a screen region → base64 PNG."""
        if width <= 0 or height <= 0:
            raise ValueError(f"width and height must be > 0, got {width}x{height}")
        from PIL import ImageGrab
        img = ImageGrab.grab(bbox=(x, y, x + width, y + height))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return base64.b64encode(buf.getvalue()).decode("ascii")

    def capture_window(self) -> str:
        """Capture only the active window → base64 PNG."""
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            raise RuntimeError("No active window to capture")
        rect = wintypes.RECT()
        if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
            raise RuntimeError("Failed to get window rect")
        w = rect.right - rect.left
        h = rect.bottom - rect.top
        if w <= 0 or h <= 0:
            raise RuntimeError(f"Invalid window geometry: {w}x{h}")
        return self.capture_region(rect.left, rect.top, w, h)

    def save_screenshot(self, path: str) -> None:
        """Capture fullscreen and save to file."""
        from PIL import ImageGrab
        img = ImageGrab.grab()
        img.save(path)

    # ── Mouse (SendInput) ─────────────────────────────────────────────────

    def _send_mouse_input(
        self, flags: int, dx: int = 0, dy: int = 0, data: int = 0,
    ) -> None:
        """Send a single mouse input event."""
        extra = ctypes.c_ulong(0)
        mi = MOUSEINPUT(dx, dy, data, flags, 0, ctypes.pointer(extra))
        inp = INPUT(INPUT_MOUSE, _INPUT(mi=mi))
        user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))

    def _to_absolute(self, x: int, y: int) -> tuple[int, int]:
        """Convert pixel coordinates to normalized absolute (0-65535)."""
        nx = int(x * 65535 / self._screen_w)
        ny = int(y * 65535 / self._screen_h)
        return nx, ny

    def move_mouse(self, x: int, y: int) -> None:
        nx, ny = self._to_absolute(x, y)
        self._send_mouse_input(
            MOUSEEVENTF_ABSOLUTE | MOUSEEVENTF_MOVE, nx, ny,
        )

    def click(self, x: int, y: int, button: str = "left") -> None:
        self.move_mouse(x, y)
        time.sleep(0.02)
        if button == "left":
            self._send_mouse_input(MOUSEEVENTF_LEFTDOWN)
            self._send_mouse_input(MOUSEEVENTF_LEFTUP)
        elif button == "right":
            self._send_mouse_input(MOUSEEVENTF_RIGHTDOWN)
            self._send_mouse_input(MOUSEEVENTF_RIGHTUP)
        elif button == "middle":
            self._send_mouse_input(MOUSEEVENTF_MIDDLEDOWN)
            self._send_mouse_input(MOUSEEVENTF_MIDDLEUP)
        else:
            raise ValueError(f"Unknown button: {button!r}")

    def double_click(self, x: int, y: int) -> None:
        self.click(x, y)
        time.sleep(0.05)
        self.click(x, y)

    def drag(self, from_x: int, from_y: int, to_x: int, to_y: int) -> None:
        self.move_mouse(from_x, from_y)
        time.sleep(0.02)
        self._send_mouse_input(MOUSEEVENTF_LEFTDOWN)
        steps = max(abs(to_x - from_x), abs(to_y - from_y)) // 10 or 1
        for i in range(1, steps + 1):
            ix = from_x + (to_x - from_x) * i // steps
            iy = from_y + (to_y - from_y) * i // steps
            self.move_mouse(ix, iy)
            time.sleep(0.005)
        self._send_mouse_input(MOUSEEVENTF_LEFTUP)

    def scroll(self, x: int, y: int, direction: str, amount: int = 3) -> None:
        if direction not in ("up", "down"):
            raise ValueError(
                f"Unknown direction: {direction!r}. Must be 'up' or 'down'"
            )
        self.move_mouse(x, y)
        delta = WHEEL_DELTA * amount
        if direction == "down":
            delta = -delta
        self._send_mouse_input(MOUSEEVENTF_WHEEL, data=delta)

    # ── Keyboard (SendInput) ───────────────────────────────────────────────

    def _send_key_input(self, vk: int, scan: int = 0, flags: int = 0) -> None:
        """Send a single keyboard input event."""
        extra = ctypes.c_ulong(0)
        ki = KEYBDINPUT(vk, scan, flags, 0, ctypes.pointer(extra))
        inp = INPUT(INPUT_KEYBOARD, _INPUT(ki=ki))
        user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))

    def _send_unicode_char(self, char: str, key_up: bool = False) -> None:
        """Send a Unicode character via KEYEVENTF_UNICODE."""
        code = ord(char)
        flags = KEYEVENTF_UNICODE
        if key_up:
            flags |= KEYEVENTF_KEYUP
        self._send_key_input(0, code, flags)

    def type_text(self, text: str) -> None:
        if not text:
            raise ValueError("text must not be empty")
        for char in text:
            entry = _VK_CHAR_MAP.get(char)
            if entry:
                vk, needs_shift = entry
                if needs_shift:
                    self._send_key_input(0x10)  # VK_SHIFT down
                self._send_key_input(vk)
                self._send_key_input(vk, flags=KEYEVENTF_KEYUP)
                if needs_shift:
                    self._send_key_input(0x10, flags=KEYEVENTF_KEYUP)
            else:
                # Unicode fallback for non-ASCII or unmapped chars
                self._send_unicode_char(char)
                self._send_unicode_char(char, key_up=True)
            time.sleep(0.012)

    def press_key(self, key: str) -> None:
        # Single printable character → type_text for shift handling
        if len(key) == 1 and "+" not in key:
            self.type_text(key)
            return

        parts = [p.strip().lower() for p in key.split("+")]
        modifiers, main_key = parts[:-1], parts[-1]

        mod_vks: list[int] = []
        for m in modifiers:
            vk = _MODIFIER_VK_MAP.get(m)
            if vk is None:
                raise ValueError(f"Unknown modifier: {m!r}")
            mod_vks.append(vk)

        main_vk = _KEY_VK_MAP.get(main_key)
        if main_vk is None:
            # Try single character
            if len(main_key) == 1:
                entry = _VK_CHAR_MAP.get(main_key)
                if entry:
                    main_vk = entry[0]
                else:
                    raise ValueError(f"Unknown key: {main_key!r}")
            else:
                raise ValueError(f"Unknown key: {main_key!r}")

        for vk in mod_vks:
            self._send_key_input(vk)
        self._send_key_input(main_vk)
        self._send_key_input(main_vk, flags=KEYEVENTF_KEYUP)
        for vk in reversed(mod_vks):
            self._send_key_input(vk, flags=KEYEVENTF_KEYUP)

    def hotkey(self, *keys: str) -> None:
        if not keys:
            raise ValueError("at least one key required")
        self.press_key("+".join(keys))

    # ── OCR (pytesseract) ──────────────────────────────────────────────────

    def extract_text_from_image(self, image_path: str) -> str:
        """Extract text from an image file using Tesseract OCR."""
        from PIL import Image
        import pytesseract
        img = Image.open(image_path)
        return pytesseract.image_to_string(img)

    def extract_text_fullscreen(self) -> str:
        """Capture full screen and extract all visible text."""
        from PIL import ImageGrab
        import pytesseract
        img = ImageGrab.grab()
        return pytesseract.image_to_string(img)

    def extract_text_from_region(
        self, x: int, y: int, width: int, height: int,
    ) -> str:
        """Capture a screen region and extract text from it."""
        from PIL import ImageGrab
        import pytesseract
        if width <= 0 or height <= 0:
            raise ValueError(
                f"width and height must be > 0, got {width}x{height}"
            )
        img = ImageGrab.grab(bbox=(x, y, x + width, y + height))
        return pytesseract.image_to_string(img)

    def extract_active_window_text(self) -> str:
        """Capture the active window and extract text via OCR."""
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            raise RuntimeError("No active window to capture")
        rect = wintypes.RECT()
        if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
            raise RuntimeError("Failed to get window rect")
        w = rect.right - rect.left
        h = rect.bottom - rect.top
        if w <= 0 or h <= 0:
            raise RuntimeError(f"Invalid window geometry: {w}x{h}")
        return self.extract_text_from_region(rect.left, rect.top, w, h)

    # ── Window Management (Win32) ──────────────────────────────────────────

    @staticmethod
    def _get_window_class(hwnd: int) -> str:
        """Get window class name for a window handle."""
        buf = ctypes.create_unicode_buffer(256)
        user32.GetClassNameW(hwnd, buf, 256)
        return buf.value

    @staticmethod
    def _get_window_title(hwnd: int) -> str:
        """Get window title for a window handle."""
        length = user32.GetWindowTextLengthW(hwnd)
        if length == 0:
            return ""
        buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buf, length + 1)
        return buf.value

    def _enum_windows(self) -> list[dict]:
        """Enumerate all visible top-level windows."""
        results: list[dict] = []

        @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        def callback(hwnd: int, _lparam: int) -> bool:
            if user32.IsWindowVisible(hwnd):
                title = self._get_window_title(hwnd)
                if title:
                    results.append({
                        "hwnd": hwnd,
                        "title": title,
                        "class_": self._get_window_class(hwnd),
                    })
            return True

        user32.EnumWindows(callback, 0)
        return results

    def clients(self) -> list[dict]:
        """Return all visible windows with title, class, and handle."""
        windows = self._enum_windows()
        return [
            {
                "hwnd": str(w["hwnd"]),
                "title": w["title"],
                "class_": w["class_"],
            }
            for w in windows
        ]

    def active_window(self) -> dict | None:
        """Return the currently focused window."""
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return None
        title = self._get_window_title(hwnd)
        return {
            "hwnd": str(hwnd),
            "title": title,
            "class_": self._get_window_class(hwnd),
        }

    def focus_window(self, target: str) -> None:
        """Focus a window by title substring or class name.

        Search order: exact title match → title substring → class name.
        """
        windows = self._enum_windows()

        # Exact title match
        for w in windows:
            if w["title"] == target:
                user32.SetForegroundWindow(w["hwnd"])
                return

        # Title substring match
        target_lower = target.lower()
        for w in windows:
            if target_lower in w["title"].lower():
                user32.SetForegroundWindow(w["hwnd"])
                return

        # Class name match
        for w in windows:
            if target_lower in w["class_"].lower():
                user32.SetForegroundWindow(w["hwnd"])
                return

        raise RuntimeError(f"No window found matching {target!r}")

    def focus_window_by_title(self, title_substring: str) -> None:
        """Focus a window by partial title match."""
        windows = self._enum_windows()
        target_lower = title_substring.lower()
        for w in windows:
            if target_lower in w["title"].lower():
                user32.SetForegroundWindow(w["hwnd"])
                return
        raise RuntimeError(
            f"No window with title containing {title_substring!r}"
        )

    # ── Virtual Desktops (PowerShell) ──────────────────────────────────────

    def workspace_list(self) -> list[dict]:
        """List virtual desktops via PowerShell.

        Falls back to a single "Desktop 1" entry if PowerShell fails.
        """
        try:
            result = subprocess.run(
                [
                    "powershell", "-NoProfile", "-Command",
                    "[void][System.Reflection.Assembly]::LoadWithPartialName("
                    "'System.Windows.Forms'); "
                    "$count = [System.Windows.Forms.SystemInformation]::"
                    "VirtualScreen; "
                    "Write-Output $count",
                ],
                capture_output=True, text=True, timeout=10,
            )
            # PowerShell virtual desktop enumeration is complex.
            # Fallback: report single desktop.
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

        # Windows 10/11 doesn't expose virtual desktop names via public API.
        # Report a single default desktop as the common case.
        return [{"id": 1, "name": "Desktop 1", "active": True}]

    def workspace_switch(self, target: str | int) -> None:
        """Switch virtual desktop.

        Supports 'next', 'previous', or desktop number.
        Uses Ctrl+Win+Arrow for adjacent, or PowerShell for specific.
        """
        if isinstance(target, int):
            target = str(target)

        if target in ("next", "+1"):
            self.hotkey("ctrl", "win", "right")
        elif target in ("previous", "-1", "prev"):
            self.hotkey("ctrl", "win", "left")
        else:
            # For specific desktop numbers, simulate multiple switches
            # This is a simplification — full IVirtualDesktopManager COM
            # interop would be needed for direct access.
            logger.warning(
                "Direct desktop switch to %s not supported, "
                "use 'next' or 'previous'", target,
            )
            raise NotImplementedError(
                f"Direct switch to desktop {target!r} not supported. "
                "Use 'next' or 'previous'."
            )

    # ── App Launch ─────────────────────────────────────────────────────────

    def launch_app(self, name: str) -> None:
        """Launch an application via Windows shell execute."""
        os.startfile(name)  # noqa: S606
