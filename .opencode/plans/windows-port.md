# Windows Port Plan — HyprAgent

## Scope

Full implementation of `harness/windows.py` + platform-aware changes across the codebase to make HyprAgent run natively on Windows 10/11. Zero changes to the Hyprland harness — pure additive.

**Target:** Windows 10/11 only. Modern Win32 APIs. No legacy support.

## Architecture Decisions

| Concern | Choice | Rationale |
|---------|--------|-----------|
| Screenshots | `PIL.ImageGrab` (already a dep) | Wraps Win32 BitBlt internally, zero new deps |
| Mouse/keyboard | Win32 `SendInput` via `ctypes` | Maximum control, no extra deps, handles Unicode via `KEYEVENTF_UNICODE` |
| Window management | Win32 `EnumWindows`/`SetForegroundWindow` via `ctypes` | No extra deps, full control |
| Virtual desktops | PowerShell `Get-Desktop` / COM `IVirtualDesktopManager` | Windows 10/11 native |
| App launch | `os.startfile()` + `subprocess.Popen` | Native Windows shell execute |
| Terminal | PowerShell via `subprocess.run(shell=True)` | Default Windows shell |
| OCR | Tesseract (same as Linux) | Already a dep, consistent behavior |
| Clipboard | `ctypes.windll.user32` + GlobalAlloc | Native Win32 clipboard, no extra dep |
| Compositor tools | Rename `hyprland_*` → `windows_*` on Windows | Clean platform separation |

## Reference Analysis

### Claude Computer Use (reference implementation)
- **Screenshot:** `gnome-screenshot`/`scrot` → PNG → base64. On Windows: `PIL.ImageGrab` is the direct equivalent.
- **Input:** `xdotool` shell commands → On Windows: `SendInput` via ctypes (same abstraction level, no subprocess).
- **Scaling:** Claude scales screenshots down to XGA (1024x768) and scales coordinates back up. We should adopt this for HiDPI/4K monitors on Windows.
- **Key insight:** The API contract is platform-agnostic. Claude sends abstract actions; our harness translates. No changes needed to MCP tool schemas.

### Manus Computer Use
- **No screen capture on local desktop.** Manus uses CLI commands + browser automation, not pixel-level control.
- **File system as memory.** Agent reads/writes `todo.md` files. We already support this via `file_*` tools.
- **Key takeaway:** Manus validates that our architecture (MCP tools + platform harness) is correct. Their CLI-only approach is simpler but less capable. Our pixel-level control is the differentiator.

## Implementation Plan

### Phase 1: WindowsHarness Core (`harness/windows.py`) — ~500 lines

#### 1.1 ctypes Structures (~80 lines)
```python
import ctypes
from ctypes import wintypes

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", ctypes.c_long), ("dy", ctypes.c_long),
        ("mouseData", wintypes.DWORD), ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD), ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]

class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD), ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]

class INPUT(ctypes.Structure):
    class _INPUT(ctypes.Union):
        _fields_ = [("mi", MOUSEINPUT), ("ki", KEYBDINPUT)]
    _fields_ = [("type", wintypes.DWORD), ("_input", _INPUT)]
```

#### 1.2 Virtual Key Map (~60 lines)
Map key names → VK codes. Covers:
- Letters: `a`-`z` → `VK_A`-`VK_Z` (0x41-0x5A)
- Digits: `0`-`9` → `VK_0`-`VK_9` (0x30-0x39)
- F-keys: `f1`-`f24` → `VK_F1`-`VK_F24`
- Special: `Return`→`VK_RETURN`, `Escape`→`VK_ESCAPE`, `Tab`→`VK_TAB`, `BackSpace`→`VK_BACK`, `Delete`→`VK_DELETE`, `space`→`VK_SPACE`
- Navigation: `Home`, `End`, `Page_Up`, `Page_Down`, `Up`, `Down`, `Left`, `Right`
- Modifiers: `ctrl`→`VK_CONTROL`, `shift`→`VK_SHIFT`, `alt`→`VK_MENU`, `super`/`win`→`VK_LWIN`

#### 1.3 Lifecycle (~30 lines)
```python
class WindowsHarness:
    name = "windows"
    
    def start(self, config=None):
        # Detect screen resolution, DPI scale factor
        self._screen_w = user32.GetSystemMetrics(0)  # SM_CXSCREEN
        self._screen_h = user32.GetSystemMetrics(1)  # SM_CYSCREEN
        # Make process DPI-aware for correct coordinates
        ctypes.windll.shcore.SetProcessDpiAwareness(2)  # PROCESS_PER_MONITOR_DPI_AWARE
        self._started = True
    
    def stop(self): pass  # No resources to release
    
    def verify(self) -> dict:
        return {"name": self.name, "started": self._started,
                "resolution": f"{self._screen_w}x{self._screen_h}"}
```

#### 1.4 Screenshot (~40 lines)
```python
def capture_fullscreen(self) -> str:
    from PIL import ImageGrab
    import io, base64
    img = ImageGrab.grab()
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")

def capture_region(self, x, y, w, h) -> str:
    from PIL import ImageGrab
    import io, base64
    img = ImageGrab.grab(bbox=(x, y, x + w, y + h))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")

def save_screenshot(self, path):
    from PIL import ImageGrab
    img = ImageGrab.grab()
    img.save(path)
```

#### 1.5 Mouse Input via SendInput (~80 lines)
```python
def _send_mouse_input(self, flags, dx=0, dy=0, data=0):
    mi = MOUSEINPUT(dx, dy, data, flags, 0, ctypes.pointer(ctypes.c_ulong(0)))
    inp = INPUT(0, MOUSEINPUT)  # INPUT_MOUSE = 0
    inp._input.mi = mi
    user32.SendInput(1, ctypes.pointer(inp), ctypes.sizeof(INPUT))

def move_mouse(self, x, y):
    # Convert to normalized absolute coordinates (0-65535)
    nx = int(x * 65535 / self._screen_w)
    ny = int(y * 65535 / self._screen_h)
    self._send_mouse_input(MOUSEEVENTF_ABSOLUTE | MOUSEEVENTF_MOVE, nx, ny)

def click(self, x, y, button="left"):
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

def double_click(self, x, y):
    self.click(x, y)
    time.sleep(0.05)
    self.click(x, y)

def drag(self, from_x, from_y, to_x, to_y):
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

def scroll(self, x, y, direction, amount=3):
    self.move_mouse(x, y)
    delta = 120 * amount  # WHEEL_DELTA = 120
    if direction == "down":
        delta = -delta
    self._send_mouse_input(MOUSEEVENTF_WHEEL, data=delta)
```

#### 1.6 Keyboard Input via SendInput (~120 lines)
```python
def _send_key_input(self, vk, scan=0, flags=0):
    ki = KEYBDINPUT(vk, scan, flags, 0, ctypes.pointer(ctypes.c_ulong(0)))
    inp = INPUT(1, KEYBDINPUT)  # INPUT_KEYBOARD = 1
    inp._input.ki = ki
    user32.SendInput(1, ctypes.pointer(inp), ctypes.sizeof(INPUT))

def _send_unicode_char(self, char, key_up=False):
    """Send a Unicode character via KEYEVENTF_UNICODE."""
    code = ord(char)
    flags = KEYEVENTF_UNICODE
    if key_up:
        flags |= KEYEVENTF_KEYUP
    self._send_key_input(0, code, flags)

def type_text(self, text):
    for char in text:
        vk_entry = _VK_CHAR_MAP.get(char)
        if vk_entry:
            vk, needs_shift = vk_entry
            if needs_shift:
                self._send_key_input(VK_SHIFT, flags=0)  # key down
            self._send_key_input(vk)
            self._send_key_input(vk, flags=KEYEVENTF_KEYUP)
            if needs_shift:
                self._send_key_input(VK_SHIFT, flags=KEYEVENTF_KEYUP)
        else:
            # Unicode fallback for non-ASCII or unmapped chars
            self._send_unicode_char(char)
            self._send_unicode_char(char, key_up=True)
        time.sleep(0.012)

def press_key(self, key):
    if len(key) == 1 and "+" not in key:
        self.type_text(key)
        return
    parts = [p.strip().lower() for p in key.split("+")]
    modifiers, main_key = parts[:-1], parts[-1]
    mod_vks = [_MODIFIER_VK_MAP[m] for m in modifiers]
    main_vk = _resolve_vk(main_key)
    for vk in mod_vks:
        self._send_key_input(vk)
    self._send_key_input(main_vk)
    self._send_key_input(main_vk, flags=KEYEVENTF_KEYUP)
    for vk in reversed(mod_vks):
        self._send_key_input(vk, flags=KEYEVENTF_KEYUP)

def hotkey(self, *keys):
    self.press_key("+".join(keys))
```

#### 1.7 OCR (~30 lines)
Same as Hyprland — capture screenshot to temp file, run pytesseract. Reuse the same pattern but use `PIL.ImageGrab` instead of `grim`.

#### 1.8 Window Management via Win32 (~100 lines)
```python
def _enum_windows(self):
    results = []
    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def callback(hwnd, _):
        if user32.IsWindowVisible(hwnd):
            length = user32.GetWindowTextLengthW(hwnd)
            buf = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buf, length + 1)
            title = buf.value
            if title:  # Skip untitled windows
                results.append({"hwnd": hwnd, "title": title})
        return True
    user32.EnumWindows(callback, 0)
    return results

def clients(self):
    windows = self._enum_windows()
    return [{"hwnd": str(w["hwnd"]), "title": w["title"],
             "class_": self._get_window_class(w["hwnd"])} for w in windows]

def active_window(self):
    hwnd = user32.GetForegroundWindow()
    # ... get title, class, return dict

def focus_window(self, target):
    # Find by title substring or class name, call SetForegroundWindow

def workspace_list(self):
    # Use PowerShell to enumerate virtual desktops
    # Or COM IVirtualDesktopManager

def workspace_switch(self, target):
    # Ctrl+Win+Left/Right for adjacent desktops
    # Or PowerShell for specific desktop

def launch_app(self, name):
    os.startfile(name)  # Shell execute

def screen_resolution(self):
    return (self._screen_w, self._screen_h)
```

### Phase 2: Platform-Aware Tool Changes

#### 2.1 `tools/browser.py` — Remove hardcoded Wayland flag (~5 lines changed)
```python
# Before:
args=["--ozone-platform=wayland"],

# After:
import platform
_args = []
if platform.system() == "Linux":
    _args = ["--ozone-platform=wayland"]
_browser = _playwright_ctx.chromium.launch(headless=False, args=_args)
```

#### 2.2 `tools/terminal.py` — Windows shell support (~15 lines changed)
```python
import platform

def terminal_run(command, cwd=None, timeout=30):
    # ... existing blocklist checks ...
    
    if platform.system() == "Windows":
        result = subprocess.run(
            command, shell=True,  # Use cmd.exe on Windows
            cwd=cwd, capture_output=True, text=True, timeout=timeout,
        )
    else:
        args = shlex.split(command)
        result = subprocess.run(
            args, cwd=cwd, capture_output=True, text=True, timeout=timeout,
        )
```

Also add Windows-specific blocked commands: `format`, `diskpart`, `reg delete`.

#### 2.3 `tools/dispatch.py` — Add windows_* routing (~15 lines added)
```python
from tools.hyprland import (
    workspace_list as _hy_workspace_list,
    # ... existing imports ...
)

def dispatch_tool(tool_name, args):
    match tool_name:
        # ... existing cases ...
        case "windows_workspace_list":
            return json.dumps(_hy_workspace_list(), indent=2)
        case "windows_workspace_switch":
            _hy_workspace_switch(args["target"])
            return "OK"
        case "windows_clients":
            return json.dumps(_hy_clients(), indent=2)
        case "windows_active_window":
            data = _hy_active_window()
            return json.dumps(data, indent=2) if data else "null"
        case "windows_focus_window":
            _hy_focus_window(args["target"])
            return "OK"
```

The `tools/hyprland.py` dispatcher already delegates to the harness, so on Windows it will call `WindowsHarness.workspace_list()` etc. — no changes needed there.

### Phase 3: MCP Server Changes

#### 3.1 `mcp_server.py` — Windows-aware doctor + tool registration (~40 lines changed)

**Doctor for Windows:**
```python
def run_doctor_windows():
    checks = {
        "Python": sys.executable,
        "Tesseract": shutil.which("tesseract"),
        "PowerShell": shutil.which("powershell"),
    }
    # Check DPI awareness
    # Check screen resolution
    # Check if running as admin (needed for SendInput to some apps)
```

**Tool registration — platform-conditional:**
```python
@server.list_tools()
async def list_tools():
    tools = [... common tools ...]
    
    if platform.system() == "Windows":
        tools.extend([
            Tool(name="windows_workspace_list", ...),
            Tool(name="windows_workspace_switch", ...),
            Tool(name="windows_clients", ...),
            Tool(name="windows_active_window", ...),
            Tool(name="windows_focus_window", ...),
        ])
    else:
        tools.extend([
            Tool(name="hyprland_workspace_list", ...),
            # ... existing hyprland tools ...
        ])
    return tools
```

**Config path:**
```python
if platform.system() == "Windows":
    _CONFIG_PATH = os.path.join(os.environ.get("APPDATA", ""), "hypr-agent", "config.yaml")
else:
    _CONFIG_PATH = os.path.expanduser("~/.config/hypr-agent/config.yaml")
```

**Skip Hyprland env detection on Windows:**
```python
async def _run():
    if platform.system() != "Windows":
        _detect_hyprland_env()
    # ... rest unchanged ...
```

### Phase 4: Dependencies & Build

#### 4.1 `pyproject.toml` — Add Windows extras
```toml
[project.optional-dependencies]
windows = [
    "pytesseract>=0.3",
]
all = ["hypragent[hyprland,windows,browser]"]
```

No new pip packages needed — `Pillow` (ImageGrab), `ctypes`, and `pytesseract` are already deps.

#### 4.2 `install-deps.ps1` — Windows dependency installer
```powershell
# Install Tesseract OCR
winget install UB-Mannheim.TesseractOCR

# Install Playwright browsers (optional)
uv run playwright install chromium

# Verify installation
tesseract --version
python -c "from PIL import ImageGrab; print('ImageGrab OK')"
```

### Phase 5: Tests

#### 5.1 `tests/test_integration.py` — Add Windows tests (~60 lines)
```python
@pytest.mark.windows
def test_windows_harness_starts():
    from harness.windows import WindowsHarness
    h = WindowsHarness()
    h.start()
    assert h._started
    h.stop()

@pytest.mark.windows
def test_windows_screenshot():
    from harness.windows import WindowsHarness
    h = WindowsHarness()
    h.start()
    b64 = h.capture_fullscreen()
    data = base64.b64decode(b64)
    assert data[1:4] == b"PNG"

@pytest.mark.windows
def test_windows_mouse_move():
    from harness.windows import WindowsHarness
    h = WindowsHarness()
    h.start()
    h.move_mouse(500, 500)  # Should not raise

@pytest.mark.windows
def test_windows_type_text():
    # ... test keyboard input ...

@pytest.mark.windows
def test_windows_window_list():
    from harness.windows import WindowsHarness
    h = WindowsHarness()
    h.start()
    clients = h.clients()
    assert isinstance(clients, list)
    assert len(clients) > 0
```

Add `windows` marker to pytest config:
```toml
[tool.pytest.ini_options]
markers = [
    "wayland: requires a running Wayland session",
    "windows: requires Windows 10/11",
]
```

### Phase 6: Documentation Updates

- **`README.md`** — Add Windows installation section
- **`docs/INSTALLATION.md`** — Windows setup instructions
- **`docs/FAQ.md`** — Windows-specific troubleshooting
- **`HARNESS_SPEC.md`** — Update Windows section from "stub" to "implemented"

## File Change Summary

| File | Action | Lines (est.) |
|------|--------|-------------|
| `harness/windows.py` | **Rewrite** (stub → full impl) | ~500 |
| `tools/browser.py` | Modify (platform-aware Chromium args) | ~5 |
| `tools/terminal.py` | Modify (Windows shell + blocklist) | ~15 |
| `tools/dispatch.py` | Modify (add windows_* routing) | ~15 |
| `mcp_server.py` | Modify (Windows doctor, tools, config path) | ~40 |
| `pyproject.toml` | Modify (add windows extras) | ~5 |
| `install-deps.ps1` | **Create** | ~20 |
| `tests/test_integration.py` | Modify (add Windows tests) | ~60 |
| `pytest.ini` / `pyproject.toml` | Modify (add windows marker) | ~2 |

**Total: ~660 lines of new/changed code across 9 files.**

## Execution Order

1. `harness/windows.py` — the core implementation (biggest piece)
2. `tools/browser.py` — quick fix
3. `tools/terminal.py` — Windows shell support
4. `tools/dispatch.py` — windows_* routing
5. `mcp_server.py` — doctor + tool registration + config path
6. `pyproject.toml` — deps + test markers
7. `install-deps.ps1` — installer script
8. `tests/test_integration.py` — Windows tests
9. Documentation updates

## Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| `SendInput` blocked by elevated apps (UAC) | Document that HyprAgent should run as admin for full control. Non-admin works for most apps. |
| DPI scaling causes wrong coordinates | `SetProcessDpiAwareness(2)` in `start()` makes coordinates physical pixels. |
| `PIL.ImageGrab` slow on 4K | Acceptable for agent use (1-2 screenshots/sec). Can optimize later with `mss` if needed. |
| Virtual desktop COM API undocumented | Use PowerShell `Get-Desktop` or `Ctrl+Win+Arrow` keystroke simulation as fallback. |
| Tesseract not in PATH on Windows | `install-deps.ps1` installs via winget. Doctor checks for it. |
| `shlex.split` breaks Windows paths | Use `shell=True` on Windows, skip shlex parsing. |

## Verification

1. `uv run pytest tests/ -m "windows" -v` — all Windows tests pass
2. `uv run pytest tests/ -m "not wayland and not windows" -v` — all platform-independent tests still pass
3. `python -c "from harness import detect_harness; h = detect_harness(); print(h.name)"` — prints `windows`
4. `python -c "from harness.windows import WindowsHarness; h = WindowsHarness(); h.start(); print(h.capture_fullscreen()[:50])"` — screenshot works
5. MCP server starts and lists windows_* tools
6. `uv run hypragent --doctor` — reports Windows dependencies correctly
7. End-to-end: Claude Code connects via MCP, takes screenshot, moves mouse, types text
