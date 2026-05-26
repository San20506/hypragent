# Harness Refactor Spec — HyprAgent v1.1

## Goal

Refactor HyprAgent so platform-specific code (Wayland/X11/macOS/Windows) is behind a harness abstraction. The tool modules call harness methods — they never call `grim`, `hyprctl`, `evdev`, or any platform binary directly. OS detection auto-selects the right harness. Dependencies are pulled as optional extras so `pip install hypragent` works everywhere.

## Architecture

### New files

```
harness/
  __init__.py       # detect_harness() + lazy imports
  base.py           # Protocol classes (ScreenshotHarness, InputHarness, CompositorHarness, Harness)
  hyprland.py       # Current code: grim + evdev/uinput + hyprctl + wl-clipboard
  x11.py             # Stub: scrot/maim + xdotool + wmctrl + xclip (implement later)
  macos.py           # Stub: screencapture + cliclick + osascript + pbcopy (implement later)
  windows.py         # Stub: PIL.ImageGrab + pyautogui + pygetwindow (implement later)
```

### base.py — Protocols

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class ScreenshotHarness(Protocol):
    def capture_fullscreen(self) -> str: ...                    # → base64 PNG
    def capture_region(self, x: int, y: int, w: int, h: int) -> str: ...  # → base64 PNG
    def save_screenshot(self, path: str) -> None: ...

@runtime_checkable
class InputHarness(Protocol):
    def move_mouse(self, x: int, y: int) -> None: ...
    def click(self, x: int, y: int, button: str = "left") -> None: ...
    def double_click(self, x: int, y: int) -> None: ...
    def drag(self, from_x: int, from_y: int, to_x: int, to_y: int) -> None: ...
    def scroll(self, x: int, y: int, direction: str, amount: int = 3) -> None: ...
    def type_text(self, text: str) -> None: ...
    def press_key(self, key: str) -> None: ...
    def hotkey(self, *keys: str) -> None: ...

@runtime_checkable
class CompositorHarness(Protocol):
    def workspace_list(self) -> list[dict]: ...
    def workspace_switch(self, target: str | int) -> None: ...
    def clients(self) -> list[dict]: ...
    def active_window(self) -> dict | None: ...
    def focus_window(self, target: str) -> None: ...
    def launch_app(self, name: str) -> None: ...              # NEW: compositor-native app launch
    def screen_resolution(self) -> tuple[int, int]: ...

@runtime_checkable  
class Harness(ScreenshotHarness, InputHarness, CompositorHarness, Protocol):
    """Full harness — all capabilities combined."""
    name: str  # human-readable: "hyprland", "x11", "macos", "windows"
    ...
```

### __init__.py — Detection

```python
import platform, os, logging

logger = logging.getLogger(__name__)

def detect_harness() -> Harness:
    """Auto-detect the correct harness for the current OS/compositor."""
    system = platform.system()
    session = os.environ.get("XDG_SESSION_TYPE", "")
    
    if system == "Linux" and session == "wayland":
        # Check for Hyprland specifically
        if os.path.exists("/usr/bin/hyprctl") or shutil.which("hyprctl"):
            from harness.hyprland import HyprlandHarness
            return HyprlandHarness()
        # Future: sway, river, etc.
        from harness.x11 import X11Harness  # fallback to XWayland
        return X11Harness()
    elif system == "Linux":
        from harness.x11 import X11Harness
        return X11Harness()
    elif system == "Darwin":
        from harness.macos import MacOSHarness
        return MacOSHarness()
    elif system == "Windows":
        from harness.windows import WindowsHarness
        return WindowsHarness()
    
    raise RuntimeError(f"No harness available for {system}/{session}")

__all__ = ["Harness", "ScreenshotHarness", "InputHarness", "CompositorHarness", "detect_harness"]
```

### hyprland.py — Move existing code

Take ALL platform-specific code from:
- `tools/screenshot.py` → `harness.hyprland.HyprlandHarness.capture_fullscreen/capture_region/save_screenshot`
- `tools/mouse.py` → `harness.hyprland.HyprlandHarness.move_mouse/click/drag/scroll`
- `tools/keyboard.py` → `harness.hyprland.HyprlandHarness.type_text/press_key/hotkey`
- `tools/ocr.py` → `harness.hyprland.HyprlandHarness.extract_text_*` (OCR is cross-platform but screenshot capture is not, so keep OCR in harness for now)
- `tools/hyprland.py` → `harness.hyprland.HyprlandHarness.workspace_list/workspace_switch/clients/active_window/focus_window/launch_app/screen_resolution`
- `agent/device_manager.py` → `harness.hyprland.HyprlandHarness.__init__` (device setup)

The `HyprlandHarness.__init__` method creates the evdev UInput devices (mouse + keyboard) and detects screen resolution via `hyprctl monitors`. The `start()` and `stop()` methods manage device lifecycle.

### Tool modules become thin dispatchers

`tools/screenshot.py`:
```python
from harness import detect_harness
_harness = None

def _get_harness():
    global _harness
    if _harness is None:
        _harness = detect_harness()
        _harness.start()
    return _harness

def capture_fullscreen() -> str:
    return _get_harness().capture_fullscreen()
# ... same pattern for every tool function
```

`tools/mouse.py`, `tools/keyboard.py`, `tools/hyprland.py` — same pattern.

### mcp_server.py changes

```python
# Replace direct device detection with harness
from harness import detect_harness
_harness = None

def _get_harness():
    global _harness
    if _harness is None:
        _harness = detect_harness()
        _harness.start()
    return _harness

# In the doctor function:
def run_doctor() -> int:
    h = _get_harness()
    print(f"  Harness ................... {h.name}")
    # harness-specific checks delegated to h.verify()
    info = h.verify()
    for k, v in info.items():
        print(f"  {k}: {v}")
```

### Stub harnesses (implement later)

`harness/x11.py`:
```python
class X11Harness:
    name = "x11"
    def start(self): raise NotImplementedError("X11 harness not yet implemented")
    # ... all protocol methods raise NotImplementedError
```

`harness/macos.py` and `harness/windows.py` — same pattern.

### pyproject.toml optional extras

```toml
[project]
dependencies = [
    "mcp>=1.0",
    "pydantic>=2.0",
    "httpx>=0.27",
    "rich>=13.0",
    "pyyaml>=6.0",
    "Pillow>=10.0",
]

[project.optional-dependencies]
hyprland = [
    "evdev>=1.6",
    "pytesseract>=0.3",
]
x11 = [
    "python-xlib>=0.33",
    "pytesseract>=0.3",
]
macos = [
    "pyobjc-framework-Quartz>=10.0",
    "pytesseract>=0.3",
]
browser = ["playwright>=1.45"]
all = ["hypragent[hyprland,browser]"]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
    "ruff>=0.6",
]
```

The core deps (`mcp`, `pydantic`, `httpx`, `rich`, `pyyaml`, `Pillow`) must work on all platforms. `evdev`, `playwright`, `pytesseract` move to extras. Lazy imports in harness drivers prevent `ImportError` on unsupported platforms.

## Rules for the refactor

1. **Zero behavior change.** The Hyprland harness must produce identical behavior to the current code. Every existing test must pass. This is a pure restructuring — no features added, no bugs fixed.
2. **Lazy imports everywhere.** Platform-specific imports (`evdev`, `pytesseract`, `subprocess` calls to `grim`/`hyprctl`) happen inside methods, not at module level. This prevents `ImportError` on non-Linux platforms.
3. **The harness singleton.** `detect_harness()` returns one harness instance for the process lifetime. Tool modules cache it in a module-level `_harness` variable. `start()` and `stop()` are idempotent.
4. **Keep the existing test structure.** Tests should still import from `tools.*` and `agent.*` — the harness is an implementation detail. Tests that need Wayland should remain `@pytest.mark.wayland`.
5. **`agent/device_manager.py` gets absorbed into `harness/hyprland.py`.** The DeviceManager concept is Hyprland-specific. X11 uses xdotool (no virtual devices). macOS uses cliclick. The harness owns its device lifecycle.
6. **`agent/loop.py` imports stay the same.** The loop calls `tools.screenshot.capture_fullscreen()` etc. — it doesn't know about harnesses. The indirection through the tool module is sufficient.
7. **Every `subprocess.run(["grim", ...)`** moves to `harness/hyprland.py`. Same for `subprocess.run(["hyprctl", ...])`. Tool modules never call a platform binary.

## Files to modify

- **Create:** `harness/__init__.py`, `harness/base.py`, `harness/hyprland.py`, `harness/x11.py`, `harness/macos.py`, `harness/windows.py`
- **Modify:** `tools/screenshot.py`, `tools/mouse.py`, `tools/keyboard.py`, `tools/ocr.py`, `tools/hyprland.py`, `mcp_server.py`, `agent/device_manager.py` (absorbed), `pyproject.toml`
- **Delete:** Nothing. `agent/device_manager.py` stays but redirects to harness.
- **Tests:** `tests/test_integration.py` — add harness detection test, verify existing tests still pass.

## Verification

1. `uv run pytest tests/ -m "not wayland" -v` — all 31 tests pass
2. `uv build` — wheel builds and includes `harness/` package
3. `python -c "from harness import detect_harness; h = detect_harness(); print(h.name)"` — prints `hyprland` on this machine
4. `python -c "from harness.base import Harness, ScreenshotHarness, InputHarness, CompositorHarness"` — all protocols importable
5. On a non-Linux machine, `pip install hypragent` (no extras) should succeed with zero compile errors
6. `pip install hypragent[hyprland]` should pull `evdev` and `pytesseract`