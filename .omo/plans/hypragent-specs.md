# HyprAgent — Chunkable Specification Chunks

> **Source**: PLAN.md (full project plan)  
> **Purpose**: Break into independent, implementable specs by ID  
> **Total Chunks**: 51 (14 milestones + 27 features + 10 system tests)

---

## Quick Index

| ID | Name | Page |
|----|------|------|
| M0 | ENV: Dev Environment Setup | §1 |
| M1 | SCREEN: Screenshot Capture | §2 |
| M2 | INPUT: Mouse & Keyboard Control | §3 |
| M3 | OCR: Screen Text Extraction | §4 |
| M4 | BACKEND: AI Backend Connection | §5 |
| M5 | MCP: MCP Server | §6 |
| M6 | LOOP: Agent Perceive-Act Loop | §7 |
| M7 | BROWSER: Browser Control | §8 |
| M8 | FILES: File Management Tools | §9 |
| M9 | TERMINAL: Terminal Command Execution | §10 |
| M10 | SAFETY: Kill Switch + Audit Log | §11 |
| M11 | MULTI-BACKEND: All 3 Backends | §12 |
| M12 | INTEGRATION: Full E2E Task | §13 |
| M13 | RELEASE: Stable v1 | §14 |
| F-01 – F-27 | Feature Specs | §15 |
| ST-01 – ST-10 | System Test Specs | §16 |

---

## Dependency Graph

```
M0 (ENV)
├── M1 (SCREEN) → M3 (OCR)
├── M2 (INPUT)
├── M4 (BACKEND)
│     └── M5 (MCP) → M6 (LOOP)
│           ├── M7 (BROWSER)
│           ├── M8 (FILES)
│           └── M9 (TERMINAL)
│                 └── M10 (SAFETY) → M11 (MULTI-BACKEND) → M12 (INTEGRATION) → M13 (RELEASE)
```

**Build Order**: Strictly sequential M0 → M13. Never start a milestone until all dependencies pass acceptance.

---

## §1. M0 — ENV: Development Environment Setup

| Attribute | Value |
|-----------|-------|
| **ID** | M0 |
| **Name** | Development Environment Ready |
| **Phase** | Phase 4 - Construct |
| **Depends On** | — (none) |
| **Priority** | P0 |

### Goal
CachyOS dev environment fully configured for HyprAgent development.

### Tasks
- [ ] Install system dependencies via `pacman` / `yay`:
  - `grim`, `slurp`, `ydotool`, `wl-clipboard`, `tesseract`, `tesseract-data-eng`
- [ ] Enable `uinput` kernel module (`modprobe uinput`)
- [ ] Add user to `input` group for `ydotool` access
- [ ] Enable and start `ydotoold` systemd service
- [ ] Install Python 3.11+ and `uv` (fast package manager)
- [ ] Initialize Python project with `pyproject.toml`
- [ ] Install Playwright and its Chromium browser

### Acceptance Criteria
- All tools callable from terminal without sudo
- `ydotoold` daemon running and accessible
- Python project scaffold ready

### Verification Command
```bash
grim --version
ydotool --version
tesseract --version
python3 --version
# All should work without sudo
```

---

## §2. M1 — SCREEN: Screenshot Capture

| Attribute | Value |
|-----------|-------|
| **ID** | M1 |
| **Name** | Screenshot Capture Working |
| **Phase** | Phase 4 - Construct |
| **Depends On** | M0 |
| **Priority** | P0 |
| **Features** | F-01, F-02 |

### Goal
`tools/screenshot.py` can capture full screen and region and return base64 PNG.

### Functions to Implement
- `capture_fullscreen() → base64_png_str`
- `capture_region(x, y, width, height) → base64_png_str`
- `save_screenshot(path: str) → None`

### MCP Tool
`take_screenshot`

### MCP Schema
```json
{
  "name": "take_screenshot",
  "description": "Capture the current screen or a region of it",
  "inputSchema": {
    "type": "object",
    "properties": {
      "region": {
        "type": "object",
        "properties": {
          "x": {"type": "integer"},
          "y": {"type": "integer"},
          "width": {"type": "integer"},
          "height": {"type": "integer"}
        },
        "required": []
      }
    }
  }
}
```

### Dependencies
`grim`, `slurp`, `Pillow`

### Acceptance Criteria
- [ ] Screenshot saved as PNG
- [ ] Base64 string passable to AI backend

---

## §3. M2 — INPUT: Mouse & Keyboard Control

| Attribute | Value |
|-----------|-------|
| **ID** | M2 |
| **Name** | Mouse + Keyboard Injection Working |
| **Phase** | Phase 4 - Construct |
| **Depends On** | M0 |
| **Priority** | P0 |
| **Features** | F-03, F-04, F-05, F-06, F-07 |

### Goal
`tools/mouse.py` and `tools/keyboard.py` can inject native Wayland input events.

### Mouse Functions
- `move_mouse(x: int, y: int) → None`
- `click(x: int, y: int, button: str = "left") → None`
- `double_click(x: int, y: int) → None`
- `drag(from_x, from_y, to_x, to_y) → None`
- `scroll(x: int, y: int, direction: str, amount: int) → None`

### Keyboard Functions
- `type_text(text: str) → None`
- `press_key(key: str) → None` (e.g. `"ctrl+c"`, `"Return"`, `"Escape"`)
- `hotkey(*keys) → None`

### MCP Tools
`mouse_move`, `mouse_click`, `mouse_drag`, `keyboard_type`, `keyboard_press`

### Dependencies
`ydotool` (daemon: `ydotoold`), `uinput` kernel module

### ⚠️ Wayland Note
`ydotool` communicates with `ydotoold` via socket. The socket path must be set via `YDOTOOL_SOCKET` env var if non-default. This must be configured at startup.

### Acceptance Criteria
- [ ] Agent can click a button and type text into a focused window

---

## §4. M3 — OCR: Screen Text Extraction

| Attribute | Value |
|-----------|-------|
| **ID** | M3 |
| **Name** | Screen Text Extraction Working |
| **Phase** | Phase 4 - Construct |
| **Depends On** | M1 |
| **Priority** | P0 |
| **Features** | F-08, F-09 |

### Goal
`tools/ocr.py` extracts text from screenshots for feeding to AI context.

### Functions
- `extract_text_from_image(image_path: str) → str`
- `extract_text_from_region(x, y, width, height) → str`
- `extract_text_fullscreen() → str`

### MCP Tool
`read_screen_text`

### Dependencies
`tesseract`, `pytesseract`, `Pillow`

### Acceptance Criteria
- [ ] Running OCR on a terminal window returns readable text with >90% accuracy

---

## §5. M4 — BACKEND: AI Backend Connection

| Attribute | Value |
|-----------|-------|
| **ID** | M4 |
| **Name** | At Least 1 AI Backend Connected |
| **Phase** | Phase 4 - Construct |
| **Depends On** | M0 |
| **Priority** | P0 |
| **Features** | F-10 |

### Goal
`agent/backends/base.py` defines the `BackendAdapter` ABC; at least Claude adapter implemented.

### BackendAdapter Interface
```python
class BackendAdapter(ABC):
    def send_message(messages: list, tools: list, images: list) → AgentResponse
    def get_model_name() → str
    def supports_vision() → bool
```

### Adapters to Implement
- `claude.py` — Anthropic API (claude-sonnet-4-5), vision-capable

### Config Schema (`config.yaml`)
```yaml
backend:
  active: claude   # options: claude | gemini | ollama
  claude:
    model: claude-sonnet-4-5
    api_key_env: ANTHROPIC_API_KEY
```

### Acceptance Criteria
- [ ] Sending a screenshot + prompt returns a coherent AI response from whichever backend is active

---

## §6. M5 — MCP: MCP Server

| Attribute | Value |
|-----------|-------|
| **ID** | M5 |
| **Name** | MCP Server Exposing All Tools |
| **Phase** | Phase 4 - Construct |
| **Depends On** | M1, M2, M3, M4 |
| **Priority** | P0 |
| **Features** | F-13, F-14 |

### Goal
`mcp_server.py` exposes all tools over MCP stdio protocol; Claude Code can connect and call tools.

### Tools Registered at Launch
- `take_screenshot`
- `mouse_move`, `mouse_click`, `mouse_drag`, `mouse_scroll`
- `keyboard_type`, `keyboard_press`
- `read_screen_text`
- `browser_open`, `browser_navigate`, `browser_click`, `browser_type`, `browser_scroll`
- `file_list`, `file_read`, `file_write`, `file_move`, `file_delete`
- `terminal_run`

### Implementation
Use `mcp` Python SDK (Anthropic's official MCP library)

### Transport
stdio (default) with optional HTTP mode via `--http` flag

### Acceptance Criteria
- [ ] `claude mcp add hypr-agent` works
- [ ] Claude Code lists all tools via `tools/list`

---

## §7. M6 — LOOP: Agent Perceive-Act Loop

| Attribute | Value |
|-----------|-------|
| **ID** | M6 |
| **Name** | Agent Perceive → Act Loop Functional |
| **Phase** | Phase 4 - Construct |
| **Depends On** | M5 |
| **Priority** | P0 |
| **Features** | F-15 |

### Goal
`agent/loop.py` runs the full perceive → reason → act cycle autonomously.

### Loop Logic
1. Take screenshot
2. Run OCR on screenshot
3. Send screenshot + OCR text + task + history to active backend
4. Parse backend response for tool calls
5. Execute tool calls via tool registry
6. Append result to history
7. Check termination: task complete / max steps reached / kill switch triggered
8. Repeat from step 1

### Configuration
```yaml
loop:
  max_steps: 20
  screenshot_on_every_step: true
  confirm_destructive_actions: true
  kill_switch_key: "ctrl+shift+escape"
```

### Acceptance Criteria
- [ ] Agent completes a simple 3-step task (open terminal → type command → read output) without human intervention

---

## §8. M7 — BROWSER: Browser Control

| Attribute | Value |
|-----------|-------|
| **ID** | M7 |
| **Name** | Browser Control via Playwright |
| **Phase** | Phase 4 - Construct |
| **Depends On** | M6 |
| **Priority** | P0 |
| **Features** | F-19, F-20, F-21 |

### Goal
`tools/browser.py` provides Playwright-based browser automation.

### Functions
- `browser_open(url: str) → None`
- `browser_navigate(url: str) → None`
- `browser_click(selector: str) → None`
- `browser_type(selector: str, text: str) → None`
- `browser_scroll(direction: str, amount: int) → None`
- `browser_screenshot() → base64_png_str`
- `browser_get_text(selector: str) → str`
- `browser_close() → None`

### MCP Tools
`browser_open`, `browser_navigate`, `browser_click`, `browser_type`, `browser_scroll`, `browser_get_text`

### Dependencies
`playwright` (chromium), running under Wayland via `--ozone-platform=wayland`

### Acceptance Criteria
- [ ] Agent fills out a web form and submits it

---

## §9. M8 — FILES: File Management Tools

| Attribute | Value |
|-----------|-------|
| **ID** | M8 |
| **Name** | File Management Tools Working |
| **Phase** | Phase 4 - Construct |
| **Depends On** | M6 |
| **Priority** | P0 |
| **Features** | F-22, F-23 |

### Goal
`tools/files.py` provides safe file system operations.

### Functions
- `file_list(path: str) → list[dict]`
- `file_read(path: str) → str`
- `file_write(path: str, content: str, confirm: bool = True) → None`
- `file_move(src: str, dst: str, confirm: bool = True) → None`
- `file_delete(path: str, confirm: bool = True) → None`
- `file_open(path: str) → None` (opens with xdg-open)

### Safety
Destructive operations (`write`, `move`, `delete`) respect `confirm_destructive_actions` config flag

### Acceptance Criteria
- [ ] Agent can list a directory, read a file, and write a modified version

---

## §10. M9 — TERMINAL: Terminal Command Execution

| Attribute | Value |
|-----------|-------|
| **ID** | M9 |
| **Name** | Terminal Command Execution Working |
| **Phase** | Phase 4 - Construct |
| **Depends On** | M6 |
| **Priority** | P0 |
| **Features** | F-24 |

### Goal
`tools/terminal.py` runs shell commands and returns structured output.

### Functions
- `terminal_run(command: str, cwd: str = None, timeout: int = 30) → TerminalResult`
  - Returns: `{ stdout, stderr, returncode, timed_out }`
- `terminal_run_interactive(command: str) → None` (opens in terminal emulator)

### Safety Controls
- Blocklist of forbidden commands (configurable)
- Timeout enforcement
- No `shell=True` for simple commands; subprocess list args

### Acceptance Criteria
- [ ] Agent runs `ls -la` and reads the output
- [ ] Blocked commands are rejected cleanly

---

## §11. M10 — SAFETY: Safety Controls

| Attribute | Value |
|-----------|-------|
| **ID** | M10 |
| **Name** | Kill Switch + Audit Log + Confirmations |
| **Phase** | Phase 5 - Test |
| **Depends On** | M6 |
| **Priority** | P0 |
| **Features** | F-16, F-17, F-18, F-25 |

### Goal
Implement safety controls before integration testing.

### Safety Features
- **Kill switch**: `ctrl+shift+escape` terminates loop within 1 second
- **Max step limiter**: configurable `max_steps`
- **Audit log**: captures every action with timestamp
- **Destructive action confirmation**: prompt user if enabled

### Acceptance Criteria
- [ ] Kill switch terminates loop within 1 second
- [ ] Audit log captures every action with timestamp

---

## §12. M11 — MULTI-BACKEND: All 3 Backends Swappable

| Attribute | Value |
|-----------|-------|
| **ID** | M11 |
| **Name** | All 3 Backends Swappable via Config |
| **Phase** | Phase 5 - Test |
| **Depends On** | M4 |
| **Priority** | P1 |
| **Features** | F-11, F-12, F-26 |

### Goal
All three backends implemented and swappable via config.

### Backends
- Claude (already in M4)
- Gemini: `gemini.py` — Google Generative AI SDK (gemini-2.5-flash)
- Ollama: `ollama.py` — Local Ollama endpoint (llava or similar)

### Config Schema
```yaml
backend:
  active: claude   # options: claude | gemini | ollama
  claude:
    model: claude-sonnet-4-5
    api_key_env: ANTHROPIC_API_KEY
  gemini:
    model: gemini-2.5-flash
    api_key_env: GEMINI_API_KEY
  ollama:
    endpoint: http://localhost:11434
    model: llava
```

### Acceptance Criteria
- [ ] Backend swap (claude → gemini → ollama) with zero code change

---

## §13. M12 — INTEGRATION: Full End-to-End Agent Task

| Attribute | Value |
|-----------|-------|
| **ID** | M12 |
| **Name** | Full End-to-End Agent Task Completes |
| **Phase** | Phase 5 - Test |
| **Depends On** | M7, M8, M9, M10, M11 |
| **Priority** | P0 |

### Goal
Complete system integration test.

### Test
ST-10 - Full end-to-end task: "Open browser, go to github.com, search for hyprland"

### Acceptance Criteria
- [ ] All 10 system tests pass
- [ ] No sudo required for any operation

---

## §14. M13 — RELEASE: Documented, Installable, Stable v1

| Attribute | Value |
|-----------|-------|
| **ID** | M13 |
| **Name** | Documented, Installable, Stable v1 |
| **Phase** | Phase 6 - Product Release |
| **Depends On** | M12 |
| **Priority** | P0 |
| **Features** | F-27 |

### Goal
Release-ready package.

### Release Checklist
- [ ] `install.sh` script for one-command CachyOS setup
- [ ] `README.md` with quickstart guide
- [ ] `config.yaml.example` with all options documented
- [ ] Systemd unit file for `ydotoold`
- [ ] All credentials via env vars — no hardcoded keys
- [ ] CLAUDE.md in repo root for Claude Code context
- [ ] Version tagged: `v1.0.0`

### Acceptance Criteria
- [ ] `install.sh` runs without errors on a fresh CachyOS install
- [ ] CLAUDE.md, README.md, and config.yaml.example are complete and accurate

---

## §15. Feature Specifications (F-01 to F-27)

### F-01 — Full Screen Capture
| | |
|---|---|
| **ID** | F-01 |
| **Milestone** | M1 (SCREEN) |
| **Priority** | P0 |
| **Function** | `capture_fullscreen() → base64_png_str` |
| **MCP Tool** | `take_screenshot` |

### F-02 — Region Capture
| | |
|---|---|
| **ID** | F-02 |
| **Milestone** | M1 (SCREEN) |
| **Priority** | P0 |
| **Function** | `capture_region(x, y, width, height) → base64_png_str` |

### F-03 — Mouse Move & Click
| | |
|---|---|
| **ID** | F-03 |
| **Milestone** | M2 (INPUT) |
| **Priority** | P0 |
| **Functions** | `move_mouse(x, y)`, `click(x, y, button)` |

### F-04 — Mouse Drag
| | |
|---|---|
| **ID** | F-04 |
| **Milestone** | M2 (INPUT) |
| **Priority** | P1 |
| **Function** | `drag(from_x, from_y, to_x, to_y)` |

### F-05 — Mouse Scroll
| | |
|---|---|
| **ID** | F-05 |
| **Milestone** | M2 (INPUT) |
| **Priority** | P1 |
| **Function** | `scroll(x, y, direction, amount)` |

### F-06 — Type Text
| | |
|---|---|
| **ID** | F-06 |
| **Milestone** | M2 (INPUT) |
| **Priority** | P0 |
| **Function** | `type_text(text: str)` |

### F-07 — Press Key Combos
| | |
|---|---|
| **ID** | F-07 |
| **Milestone** | M2 (INPUT) |
| **Priority** | P0 |
| **Functions** | `press_key(key)`, `hotkey(*keys)` |

### F-08 — OCR Full Screen
| | |
|---|---|
| **ID** | F-08 |
| **Milestone** | M3 (OCR) |
| **Priority** | P0 |
| **Function** | `extract_text_fullscreen() → str` |

### F-09 — OCR Region
| | |
|---|---|
| **ID** | F-09 |
| **Milestone** | M3 (OCR) |
| **Priority** | P1 |
| **Function** | `extract_text_from_region(x, y, width, height)` |

### F-10 — Claude Backend
| | |
|---|---|
| **ID** | F-10 |
| **Milestone** | M4 (BACKEND) |
| **Priority** | P0 |
| **Adapter** | `agent/backends/claude.py` |
| **Model** | claude-sonnet-4-5 |

### F-11 — Gemini Backend
| | |
|---|---|
| **ID** | F-11 |
| **Milestone** | M11 (MULTI-BACKEND) |
| **Priority** | P1 |
| **Adapter** | `agent/backends/gemini.py` |
| **Model** | gemini-2.5-flash |

### F-12 — Ollama Backend
| | |
|---|---|
| **ID** | F-12 |
| **Milestone** | M11 (MULTI-BACKEND) |
| **Priority** | P1 |
| **Adapter** | `agent/backends/ollama.py` |
| **Model** | llava |

### F-13 — MCP Stdio Server
| | |
|---|---|
| **ID** | F-13 |
| **Milestone** | M5 (MCP) |
| **Priority** | P0 |
| **Implementation** | `mcp` Python SDK |

### F-14 — MCP HTTP Server
| | |
|---|---|
| **ID** | F-14 |
| **Milestone** | M5 (MCP) |
| **Priority** | P2 |
| **Flag** | `--http` |

### F-15 — Agent Perceive Loop
| | |
|---|---|
| **ID** | F-15 |
| **Milestone** | M6 (LOOP) |
| **Priority** | P0 |
| **File** | `agent/loop.py` |

### F-16 — Max Step Limiter
| | |
|---|---|
| **ID** | F-16 |
| **Milestone** | M10 (SAFETY) |
| **Priority** | P0 |
| **Config** | `loop.max_steps` |

### F-17 — Kill Switch
| | |
|---|---|
| **ID** | F-17 |
| **Milestone** | M10 (SAFETY) |
| **Priority** | P0 |
| **Key** | `ctrl+shift+escape` |

### F-18 — Audit Log
| | |
|---|---|
| **ID** | F-18 |
| **Milestone** | M10 (SAFETY) |
| **Priority** | P0 |

### F-19 — Browser Open/Navigate
| | |
|---|---|
| **ID** | F-19 |
| **Milestone** | M7 (BROWSER) |
| **Priority** | P0 |
| **Functions** | `browser_open(url)`, `browser_navigate(url)` |

### F-20 — Browser Form Fill
| | |
|---|---|
| **ID** | F-20 |
| **Milestone** | M7 (BROWSER) |
| **Priority** | P0 |
| **Functions** | `browser_click(selector)`, `browser_type(selector, text)` |

### F-21 — Browser Screenshot
| | |
|---|---|
| **ID** | F-21 |
| **Milestone** | M7 (BROWSER) |
| **Priority** | P1 |
| **Function** | `browser_screenshot() → base64_png_str` |

### F-22 — File List/Read
| | |
|---|---|
| **ID** | F-22 |
| **Milestone** | M8 (FILES) |
| **Priority** | P0 |
| **Functions** | `file_list(path)`, `file_read(path)` |

### F-23 — File Write/Move/Delete
| | |
|---|---|
| **ID** | F-23 |
| **Milestone** | M8 (FILES) |
| **Priority** | P0 |
| **Functions** | `file_write`, `file_move`, `file_delete` |

### F-24 — Terminal Run
| | |
|---|---|
| **ID** | F-24 |
| **Milestone** | M9 (TERMINAL) |
| **Priority** | P0 |
| **Function** | `terminal_run(command, cwd, timeout) → TerminalResult` |

### F-25 — Destructive Action Confirm
| | |
|---|---|
| **ID** | F-25 |
| **Milestone** | M10 (SAFETY) |
| **Priority** | P0 |
| **Config** | `loop.confirm_destructive_actions` |

### F-26 — Config-Driven Backend Swap
| | |
|---|---|
| **ID** | F-26 |
| **Milestone** | M11 (MULTI-BACKEND) |
| **Priority** | P0 |

### F-27 — Install Script
| | |
|---|---|
| **ID** | F-27 |
| **Milestone** | M13 (RELEASE) |
| **Priority** | P0 |
| **File** | `install.sh` |

---

## §16. System Test Specifications (ST-01 to ST-10)

### ST-01 — Screenshot → OCR → AI Roundtrip

| | |
|---|---|
| **ID** | ST-01 |
| **Milestone** | All (integration) |
| **Description** | Full screenshot → OCR → AI reasoning roundtrip |

**Test Steps**:
1. Capture full screen screenshot
2. Run OCR on screenshot
3. Send screenshot + OCR text to backend
4. Verify coherent response received

**Expected**: PASS

---

### ST-02 — Mouse Click Accuracy

| | |
|---|---|
| **ID** | ST-02 |
| **Milestone** | M2 |
| **Description** | Mouse click lands within 5px of target |

**Test Steps**:
1. Move mouse to known coordinate
2. Capture screenshot at that position
3. Verify click position via OCR or visual inspection

**Expected**: Click within 5px of target

---

### ST-03 — Keyboard Type Accuracy

| | |
|---|---|
| **ID** | ST-03 |
| **Milestone** | M2 |
| **Description** | Keyboard type reproduces string exactly including special chars |

**Test Steps**:
1. Open text editor
2. Type string with special characters: `Hello World! @#$%^&*()`
3. Verify output matches exactly

**Expected**: Exact reproduction

---

### ST-04 — Browser Form Fill

| | |
|---|---|
| **ID** | ST-04 |
| **Milestone** | M7 |
| **Description** | Browser opens URL and fills form correctly |

**Test Steps**:
1. Open browser to test form page (e.g., httpbin.org/forms/post)
2. Fill form fields
3. Submit form
4. Verify submission success

**Expected**: Form submitted successfully

---

### ST-05 — File Encoding Preservation

| | |
|---|---|
| **ID** | ST-05 |
| **Milestone** | M8 |
| **Description** | File read/write preserves encoding |

**Test Steps**:
1. Write file with UTF-8 content (including non-ASCII)
2. Read file back
3. Verify content matches

**Expected**: UTF-8 preserved

---

### ST-06 — Terminal Command Output

| | |
|---|---|
| **ID** | ST-06 |
| **Milestone** | M9 |
| **Description** | Terminal command returns correct stdout |

**Test Steps**:
1. Run `ls -la` command
2. Parse stdout
3. Verify expected files listed

**Expected**: Correct stdout returned

---

### ST-07 — Kill Switch Response Time

| | |
|---|---|
| **ID** | ST-07 |
| **Milestone** | M10 |
| **Description** | Kill switch terminates loop within 1 second |

**Test Steps**:
1. Start agent loop
2. Press kill switch key combo
3. Measure time to termination

**Expected**: Terminated within 1 second

---

### ST-08 — Audit Log Completeness

| | |
|---|---|
| **ID** | ST-08 |
| **Milestone** | M10 |
| **Description** | Audit log captures every action with timestamp |

**Test Steps**:
1. Run several agent actions
2. Check audit log
3. Verify each action recorded with timestamp

**Expected**: All actions logged

---

### ST-09 — Backend Swap Verification

| | |
|---|---|
| **ID** | ST-09 |
| **Milestone** | M11 |
| **Description** | Backend swap (claude → gemini → ollama) with zero code change |

**Test Steps**:
1. Configure claude backend, verify response
2. Change config to gemini, verify response
3. Change config to ollama, verify response

**Expected**: All backends work via config change only

---

### ST-10 — Full E2E Task

| | |
|---|---|
| **ID** | ST-10 |
| **Milestone** | M12 |
| **Description** | Full end-to-end task: "Open browser, go to github.com, search for hyprland" |

**Test Steps**:
1. Issue task: "Open browser, go to github.com, search for hyprland"
2. Agent opens browser
3. Agent navigates to github.com
4. Agent performs search
5. Verify search results page loaded

**Expected**: Task completed successfully

---

## Spec Index Summary

| Category | ID Range | Count |
|----------|----------|-------|
| Milestones | M0–M13 | 14 |
| Features | F-01–F-27 | 27 |
| System Tests | ST-01–ST-10 | 10 |
| **Total** | | **51** |

### Feature-to-Milestone Mapping

| Milestone | Features |
|-----------|----------|
| M1 (SCREEN) | F-01, F-02 |
| M2 (INPUT) | F-03, F-04, F-05, F-06, F-07 |
| M3 (OCR) | F-08, F-09 |
| M4 (BACKEND) | F-10 |
| M5 (MCP) | F-13, F-14 |
| M6 (LOOP) | F-15 |
| M7 (BROWSER) | F-19, F-20, F-21 |
| M8 (FILES) | F-22, F-23 |
| M9 (TERMINAL) | F-24 |
| M10 (SAFETY) | F-16, F-17, F-18, F-25 |
| M11 (MULTI-BACKEND) | F-11, F-12, F-26 |
| M13 (RELEASE) | F-27 |
