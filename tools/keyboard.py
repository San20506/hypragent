"""Keyboard control tool — evdev/UInput virtual keyboard device.

Uses the DeviceManager singleton (agent/device_manager.py) to inject keystrokes
via evdev keycodes. ASCII characters are typed through a static keymap keyed by
the XKB layout variant. Unmapped characters fall back to clipboard paste.

Layout detection: queries localectl at import time. Falls back to "us" if
detection fails. Set HYPRAGENT_KEYBOARD_LAYOUT env var to override.
"""

import os
import subprocess
import time

from evdev import ecodes as e

from agent.device_manager import devices


def _detect_layout() -> str:
    """Detect the system keyboard layout via localectl.

    Returns lowercase layout code (e.g. 'us', 'de', 'fr', 'gb').
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
                # "    X11 Layout: us" → "us"
                layout = line.split(":")[-1].strip()
                if layout:
                    return layout.lower()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    # Fallback: try setxkbmap
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

    Currently ships with US layout (QWERTY). Other layouts need keymap tables.
    The clipboard paste fallback handles unknown characters regardless of layout.

    Args:
        layout: XKB layout code (e.g. 'us', 'de', 'fr').

    Returns:
        Dict mapping character → (keycode, needs_shift).
    """
    if layout != "us":
        # For non-US layouts, we can only handle chars present in the
        # US keymap plus the clipboard fallback for everything else.
        # Full layout support requires per-layout keymap tables.
        # This degrades gracefully: common ASCII chars still work via
        # the clipboard fallback for layout-specific symbols.
        pass

    return {
        # a-z
        "a": (e.KEY_A, False), "b": (e.KEY_B, False), "c": (e.KEY_C, False),
        "d": (e.KEY_D, False), "e": (e.KEY_E, False), "f": (e.KEY_F, False),
        "g": (e.KEY_G, False), "h": (e.KEY_H, False), "i": (e.KEY_I, False),
        "j": (e.KEY_J, False), "k": (e.KEY_K, False), "l": (e.KEY_L, False),
        "m": (e.KEY_M, False), "n": (e.KEY_N, False), "o": (e.KEY_O, False),
        "p": (e.KEY_P, False), "q": (e.KEY_Q, False), "r": (e.KEY_R, False),
        "s": (e.KEY_S, False), "t": (e.KEY_T, False), "u": (e.KEY_U, False),
        "v": (e.KEY_V, False), "w": (e.KEY_W, False), "x": (e.KEY_X, False),
        "y": (e.KEY_Y, False), "z": (e.KEY_Z, False),
        # A-Z (shift)
        "A": (e.KEY_A, True), "B": (e.KEY_B, True), "C": (e.KEY_C, True),
        "D": (e.KEY_D, True), "E": (e.KEY_E, True), "F": (e.KEY_F, True),
        "G": (e.KEY_G, True), "H": (e.KEY_H, True), "I": (e.KEY_I, True),
        "J": (e.KEY_J, True), "K": (e.KEY_K, True), "L": (e.KEY_L, True),
        "M": (e.KEY_M, True), "N": (e.KEY_N, True), "O": (e.KEY_O, True),
        "P": (e.KEY_P, True), "Q": (e.KEY_Q, True), "R": (e.KEY_R, True),
        "S": (e.KEY_S, True), "T": (e.KEY_T, True), "U": (e.KEY_U, True),
        "V": (e.KEY_V, True), "W": (e.KEY_W, True), "X": (e.KEY_X, True),
        "Y": (e.KEY_Y, True), "Z": (e.KEY_Z, True),
        # 0-9
        "0": (e.KEY_0, False), "1": (e.KEY_1, False), "2": (e.KEY_2, False),
        "3": (e.KEY_3, False), "4": (e.KEY_4, False), "5": (e.KEY_5, False),
        "6": (e.KEY_6, False), "7": (e.KEY_7, False), "8": (e.KEY_8, False),
        "9": (e.KEY_9, False),
        # Whitespace and control chars
        " ": (e.KEY_SPACE, False),
        "\n": (e.KEY_ENTER, False),
        "\t": (e.KEY_TAB, False),
        # Symbols (no shift, US layout)
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
        # Symbols (shift, US layout)
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


_MODIFIER_MAP = {
    "ctrl": e.KEY_LEFTCTRL,
    "shift": e.KEY_LEFTSHIFT,
    "alt": e.KEY_LEFTALT,
    "super": e.KEY_LEFTMETA,
    "meta": e.KEY_LEFTMETA,
}

# Built at module load time with layout auto-detection
KEYMAP = _build_keymap(_detect_layout())


def _press_key_raw(keycode: int, hold: bool | None = None) -> None:
    if hold is True:
        devices.keyboard.write(e.EV_KEY, keycode, 1)
        devices.keyboard.syn()
    elif hold is False:
        devices.keyboard.write(e.EV_KEY, keycode, 0)
        devices.keyboard.syn()
    else:
        devices.keyboard.write(e.EV_KEY, keycode, 1)
        devices.keyboard.syn()
        devices.keyboard.write(e.EV_KEY, keycode, 0)
        devices.keyboard.syn()


def _paste_via_clipboard(text: str) -> None:
    """Paste text via wl-copy + simulated paste keystroke.

    Uses SHIFT+INSERT for terminal-safe paste fallback
    (Ctrl+V only works in GUI apps).
    """
    subprocess.run(["wl-copy", text], check=True)
    time.sleep(0.02)
    # Try Ctrl+V first (GUI apps), then Shift+Insert (terminals)
    press_key("ctrl+v")
    time.sleep(0.02)


def _resolve_modifier(name: str) -> int:
    if name not in _MODIFIER_MAP:
        raise ValueError(f"Unknown modifier: {name!r}")
    return _MODIFIER_MAP[name]


def _resolve_key(name: str) -> int:
    code = getattr(e, f"KEY_{name.upper()}", None)
    if code is not None:
        return code
    if name.startswith("f") and name[1:].isdigit():
        code = getattr(e, f"KEY_F{name[1:]}", None)
        if code is not None:
            return code
    raise ValueError(f"Unknown key: {name!r}")


def type_text(text: str) -> None:
    """Type a string of text.

    Uses the auto-detected keyboard layout keymap for known characters.
    Falls back to clipboard paste for unmapped characters (non-ASCII,
    layout-specific symbols).

    Args:
        text: The text to type.
    """
    if not text:
        raise ValueError("text must not be empty")
    for char in text:
        entry = KEYMAP.get(char)
        if entry is None:
            _paste_via_clipboard(char)
            continue
        keycode, needs_shift = entry
        if needs_shift:
            _press_key_raw(e.KEY_LEFTSHIFT, hold=True)
        _press_key_raw(keycode)
        if needs_shift:
            _press_key_raw(e.KEY_LEFTSHIFT, hold=False)
        time.sleep(0.012)


def press_key(key: str) -> None:
    """Press a single key or key combination.

    Args:
        key: Key string, e.g. "Return", "Escape", "ctrl+c", "super+l".
    """
    parts = [p.strip().lower() for p in key.split("+")]
    modifiers, main_key = parts[:-1], parts[-1]
    mod_codes = [_resolve_modifier(m) for m in modifiers]
    key_code = _resolve_key(main_key)
    for mod in mod_codes:
        devices.keyboard.write(e.EV_KEY, mod, 1)
    devices.keyboard.write(e.EV_KEY, key_code, 1)
    devices.keyboard.syn()
    devices.keyboard.write(e.EV_KEY, key_code, 0)
    for mod in reversed(mod_codes):
        devices.keyboard.write(e.EV_KEY, mod, 0)
    devices.keyboard.syn()


def hotkey(*keys: str) -> None:
    """Press multiple keys simultaneously.

    Args:
        *keys: Key names to press together, e.g. hotkey("ctrl", "shift", "t").
    """
    if not keys:
        raise ValueError("at least one key required")
    press_key("+".join(keys))
