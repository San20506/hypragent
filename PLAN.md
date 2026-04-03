# PLAN.md — HyprAgent: Full General-Purpose Computer Use Agent
> Platform: CachyOS + Hyprland (Wayland) | Model-Agnostic | MCP-First Architecture
> Last Updated: 2026-04-02 | SDLC Phase: Planning → Design

---

## Table of Contents
1. [Project Overview](#1-project-overview)
2. [Architecture Summary](#2-architecture-summary)
3. [Milestone Map](#3-milestone-map)
4. [Phase-by-Phase Breakdown](#4-phase-by-phase-breakdown)
5. [Feature Registry](#5-feature-registry)
6. [Tool Inventory](#6-tool-inventory)
7. [Dependency Graph](#7-dependency-graph)
8. [Risk Register](#8-risk-register)
9. [Definition of Done](#9-definition-of-done)

---

## 1. Project Overview

**HyprAgent** is a native, model-agnostic computer use agent built for Hyprland on Wayland. It replicates and extends the Claude Computer Use capability (available on macOS) for a CachyOS/Arch Linux environment. The agent exposes all computer interaction capabilities as MCP (Model Context Protocol) tools, allowing any compatible AI client — Claude Code, OpenCode, or custom — to drive desktop automation.

| Attribute | Value |
|---|---|
| Project Name | HyprAgent |
| Target OS | CachyOS (Arch Linux), Hyprland, Wayland |
| Agent Brain | Model-agnostic (Claude / Gemini / Ollama) |
| Orchestration Protocol | MCP (Model Context Protocol) |
| Execution Environment | Native live desktop — no Docker, no sandbox |
| Primary Language | Python 3.11+ |
| Build Tool | Claude Code (guided construction) |

---

## 2. Architecture Summary

```
┌─────────────────────────────────────────────────────┐
│                   AI Client Layer                    │
│     Claude Code / OpenCode / Custom MCP Client       │
└──────────────────────┬──────────────────────────────┘
                       │ MCP Protocol (stdio / HTTP)
┌──────────────────────▼──────────────────────────────┐
│                  MCP Server (mcp_server.py)          │
│         tools/list  ·  tools/call  ·  routing        │
└──────┬──────────┬──────────┬───────────┬────────────┘
       │          │          │           │
┌──────▼──┐ ┌────▼────┐ ┌───▼───┐ ┌────▼──────┐
│ Screen  │ │  Input  │ │  OCR  │ │  Browser  │
│ Capture │ │ Control │ │Engine │ │ Playwright│
│  grim   │ │ydotool  │ │tessr. │ │           │
└──────┬──┘ └────┬────┘ └───┬───┘ └────┬──────┘
       │          │          │           │
┌──────▼──────────▼──────────▼───────────▼──────────┐
│              Agent Loop (loop.py)                  │
│     Perceive → Reason → Act → Log → Repeat         │
└──────────────────────┬────────────────────────────┘
                       │
┌──────────────────────▼────────────────────────────┐
│              Backend Adapter Layer                  │
│   claude.py  |  gemini.py  |  ollama.py            │
│              BackendAdapter (base.py)               │
└───────────────────────────────────────────────────┘
```

---

## 3. Milestone Map

| Milestone | ID | Description | Phase | Depends On |
|---|---|---|---|---|
| M0 | ENV | Dev environment ready on CachyOS | Phase 4 | — |
| M1 | SCREEN | Screenshot capture working | Phase 4 | M0 |
| M2 | INPUT | Mouse + keyboard injection working | Phase 4 | M0 |
| M3 | OCR | Screen text extraction working | Phase 4 | M1 |
| M4 | BACKEND | At least 1 AI backend connected | Phase 4 | M0 |
| M5 | MCP | MCP server exposing all tools | Phase 4 | M1–M4 |
| M6 | LOOP | Agent perceive→act loop functional | Phase 4 | M5 |
| M7 | BROWSER | Browser control via Playwright | Phase 4 | M6 |
| M8 | FILES | File management tools working | Phase 4 | M6 |
| M9 | TERMINAL | Terminal command execution working | Phase 4 | M6 |
| M10 | SAFETY | Kill switch + audit log + confirmations | Phase 5 | M6 |
| M11 | MULTI-BACKEND | All 3 backends swappable via config | Phase 5 | M4 |
| M12 | INTEGRATION | Full end-to-end agent task completes | Phase 5 | M7–M11 |
| M13 | RELEASE | Documented, installable, stable v1 | Phase 6 | M12 |

---

## 4. Phase-by-Phase Breakdown

---

### Phase 2 — Requirements & Planning ✅ (Current)

**Deliverables:**
- [x] PLAN.md (this document)
- [x] PRD.md
- [x] CLAUDE.md (Claude Code guidance)

**Key Decisions Locked:**
- Wayland-native stack (no XWayland)
- MCP as the orchestration protocol
- `ydotool` for input injection (requires `uinput` kernel module)
- `grim` for screenshots
- `tesseract` for OCR
- `playwright` for browser automation
- Python 3.11+ runtime

---

### Phase 3 — Design

**Deliverables:**
- BackendAdapter interface contract
- MCP tool schema definitions (JSON Schema per tool)
- Agent loop state machine
- Config schema (`config.yaml` spec)
- Wayland permission setup sequence (`uinput` group, `ydotoold` daemon)
- Project scaffold (directory structure, empty modules)

**Key Design Decisions to Make:**
- MCP transport: stdio vs HTTP (recommend stdio for Claude Code compatibility)
- Screenshot format: PNG vs JPEG (PNG recommended for OCR accuracy)
- Loop termination strategy: max steps vs confidence threshold vs both
- Clipboard strategy for text injection: `wl-clipboard` vs direct ydotool typing

---

### Phase 4 — Construct

Broken into 9 sub-milestones below.

#### M0 — Environment Setup
**Goal:** CachyOS dev environment fully configured for HyprAgent development.

Tasks:
- Install system dependencies via `pacman` / `yay`
  - `grim`, `slurp`, `ydotool`, `wl-clipboard`, `tesseract`, `tesseract-data-eng`
- Enable `uinput` kernel module (`modprobe uinput`)
- Add user to `input` group for `ydotool` access
- Enable and start `ydotoold` systemd service
- Install Python 3.11+ and `uv` (fast package manager)
- Initialise Python project with `pyproject.toml`
- Install Playwright and its Chromium browser

Acceptance: All tools callable from terminal without sudo.

---

#### M1 — Screenshot Capture (FR-01)
**Goal:** `tools/screenshot.py` can capture full screen and region and return base64 PNG.

Functions to implement:
- `capture_fullscreen() → base64_png_str`
- `capture_region(x, y, width, height) → base64_png_str`
- `save_screenshot(path: str) → None`

MCP Tool exposed: `take_screenshot`

MCP Schema:
```json
{
  "name": "take_screenshot",
  "description": "Capture the current screen or a region of it",
  "inputSchema": {
    "type": "object",
    "properties": {
      "region": {
        "type": "object",
        "properties": { "x": {"type":"integer"}, "y": {"type":"integer"},
                        "width": {"type":"integer"}, "height": {"type":"integer"} },
        "required": []
      }
    }
  }
}
```

Dependencies: `grim`, `slurp` (optional for interactive region), `Pillow`

Acceptance: Screenshot saved as PNG; base64 string passable to AI backend.

---

#### M2 — Mouse & Keyboard Control (FR-02, FR-03)
**Goal:** `tools/mouse.py` and `tools/keyboard.py` can inject native Wayland input events.

Mouse functions:
- `move_mouse(x: int, y: int) → None`
- `click(x: int, y: int, button: str = "left") → None`
- `double_click(x: int, y: int) → None`
- `drag(from_x, from_y, to_x, to_y) → None`
- `scroll(x: int, y: int, direction: str, amount: int) → None`

Keyboard functions:
- `type_text(text: str) → None`
- `press_key(key: str) → None` (e.g. `"ctrl+c"`, `"Return"`, `"Escape"`)
- `hotkey(*keys) → None`

MCP Tools exposed: `mouse_move`, `mouse_click`, `mouse_drag`, `keyboard_type`, `keyboard_press`

Dependencies: `ydotool` (daemon: `ydotoold`), `uinput` kernel module

⚠️ Wayland Note: `ydotool` communicates with `ydotoold` via socket. The socket path must be set via `YDOTOOL_SOCKET` env var if non-default. This must be configured at startup.

Acceptance: Agent can click a button and type text into a focused window.

---

#### M3 — OCR / Screen Reading (FR-04)
**Goal:** `tools/ocr.py` extracts text from screenshots for feeding to AI context.

Functions:
- `extract_text_from_image(image_path: str) → str`
- `extract_text_from_region(x, y, width, height) → str`
- `extract_text_fullscreen() → str`

MCP Tool exposed: `read_screen_text`

Dependencies: `tesseract`, `pytesseract`, `Pillow`

Acceptance: Running OCR on a terminal window returns readable text with >90% accuracy.

---

#### M4 — Backend Adapter (FR-08)
**Goal:** `agent/backends/base.py` defines the `BackendAdapter` ABC; at least Claude adapter implemented.

BackendAdapter interface:
```
class BackendAdapter(ABC):
    def send_message(messages: list, tools: list, images: list) → AgentResponse
    def get_model_name() → str
    def supports_vision() → bool
```

Adapters to implement:
- `claude.py` — Anthropic API (claude-sonnet-4-5), vision-capable
- `gemini.py` — Google Generative AI SDK (gemini-2.5-flash), vision-capable
- `ollama.py` — Local Ollama endpoint (llava or similar), vision-capable

Config-driven selection in `config.yaml`:
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

Acceptance: Sending a screenshot + prompt returns a coherent AI response from whichever backend is active.

---

#### M5 — MCP Server (FR-09)
**Goal:** `mcp_server.py` exposes all tools over MCP stdio protocol; Claude Code can connect and call tools.

Tools registered at launch:
- `take_screenshot`
- `mouse_move`, `mouse_click`, `mouse_drag`, `mouse_scroll`
- `keyboard_type`, `keyboard_press`
- `read_screen_text`
- `browser_open`, `browser_navigate`, `browser_click`, `browser_type`, `browser_scroll`
- `file_list`, `file_read`, `file_write`, `file_move`, `file_delete`
- `terminal_run`

MCP server implementation using `mcp` Python SDK (Anthropic's official MCP library).

Transport: stdio (default) with optional HTTP mode via `--http` flag.

Acceptance: `claude mcp add hypr-agent` works; Claude Code lists all tools via `tools/list`.

---

#### M6 — Agent Loop (FR-09 continued)
**Goal:** `agent/loop.py` runs the full perceive → reason → act cycle autonomously.

Loop logic:
1. Take screenshot
2. Run OCR on screenshot
3. Send screenshot + OCR text + task + history to active backend
4. Parse backend response for tool calls
5. Execute tool calls via tool registry
6. Append result to history
7. Check termination: task complete / max steps reached / kill switch triggered
8. Repeat from step 1

Configuration:
```yaml
loop:
  max_steps: 20
  screenshot_on_every_step: true
  confirm_destructive_actions: true
  kill_switch_key: "ctrl+shift+escape"
```

Acceptance: Agent completes a simple 3-step task (open terminal → type command → read output) without human intervention.

---

#### M7 — Browser Control (FR-05)
**Goal:** `tools/browser.py` provides Playwright-based browser automation.

Functions:
- `browser_open(url: str) → None`
- `browser_navigate(url: str) → None`
- `browser_click(selector: str) → None`
- `browser_type(selector: str, text: str) → None`
- `browser_scroll(direction: str, amount: int) → None`
- `browser_screenshot() → base64_png_str`
- `browser_get_text(selector: str) → str`
- `browser_close() → None`

MCP Tools exposed: `browser_open`, `browser_navigate`, `browser_click`, `browser_type`, `browser_scroll`, `browser_get_text`

Dependencies: `playwright` (chromium), running under Wayland via `--ozone-platform=wayland`

Acceptance: Agent fills out a web form and submits it.

---

#### M8 — File Management (FR-06)
**Goal:** `tools/files.py` provides safe file system operations.

Functions:
- `file_list(path: str) → list[dict]`
- `file_read(path: str) → str`
- `file_write(path: str, content: str, confirm: bool = True) → None`
- `file_move(src: str, dst: str, confirm: bool = True) → None`
- `file_delete(path: str, confirm: bool = True) → None`
- `file_open(path: str) → None` (opens with xdg-open)

Safety: Destructive operations (`write`, `move`, `delete`) respect `confirm_destructive_actions` config flag and prompt user if enabled.

Acceptance: Agent can list a directory, read a file, and write a modified version.

---

#### M9 — Terminal Execution (FR-07)
**Goal:** `tools/terminal.py` runs shell commands and returns structured output.

Functions:
- `terminal_run(command: str, cwd: str = None, timeout: int = 30) → TerminalResult`
  - Returns: `{ stdout, stderr, returncode, timed_out }`
- `terminal_run_interactive(command: str) → None` (opens in terminal emulator)

Safety controls:
- Blocklist of forbidden commands (configurable)
- Timeout enforcement
- No shell=True for simple commands; subprocess list args

Acceptance: Agent runs `ls -la` and reads the output; blocked commands are rejected cleanly.

---

### Phase 5 — Test

#### System Tests
- ST-01: Full screenshot → OCR → AI reasoning roundtrip
- ST-02: Mouse click lands within 5px of target
- ST-03: Keyboard type reproduces string exactly including special chars
- ST-04: Browser opens URL and fills form correctly
- ST-05: File read/write preserves encoding
- ST-06: Terminal command returns correct stdout
- ST-07: Kill switch terminates loop within 1 second
- ST-08: Audit log captures every action with timestamp
- ST-09: Backend swap (claude → gemini → ollama) with zero code change
- ST-10: Full end-to-end task: "Open Firefox, go to github.com, search for hyprland"

#### Test Summary Checklist
- [ ] All 10 system tests pass
- [ ] No sudo required for any operation
- [ ] `ydotoold` daemon auto-starts on login
- [ ] MCP server connects cleanly to Claude Code
- [ ] Config swap between backends verified

---

### Phase 6 — Product Release

**Release Checklist:**
- [ ] `install.sh` script for one-command CachyOS setup
- [ ] `README.md` with quickstart guide
- [ ] `config.yaml.example` with all options documented
- [ ] Systemd unit file for `ydotoold`
- [ ] All credentials via env vars — no hardcoded keys
- [ ] CLAUDE.md in repo root for Claude Code context
- [ ] Version tagged: `v1.0.0`

---

### Phase 7 — Post Implementation

**Planned Enhancements (v1.1+):**
- Multi-monitor support (grim `-o` output flag)
- Voice command input (whisper.cpp integration)
- Task queue — batch multiple tasks
- Web UI dashboard for audit log review
- Plugin system for custom tools
- Notification on task completion (libnotify)

---

## 5. Feature Registry

| ID | Feature | Priority | Milestone | Status |
|---|---|---|---|---|
| F-01 | Full screen capture | P0 | M1 | Pending |
| F-02 | Region capture | P0 | M1 | Pending |
| F-03 | Mouse move & click | P0 | M2 | Pending |
| F-04 | Mouse drag | P1 | M2 | Pending |
| F-05 | Mouse scroll | P1 | M2 | Pending |
| F-06 | Type text | P0 | M2 | Pending |
| F-07 | Press key combos | P0 | M2 | Pending |
| F-08 | OCR full screen | P0 | M3 | Pending |
| F-09 | OCR region | P1 | M3 | Pending |
| F-10 | Claude backend | P0 | M4 | Pending |
| F-11 | Gemini backend | P1 | M11 | Pending |
| F-12 | Ollama backend | P1 | M11 | Pending |
| F-13 | MCP stdio server | P0 | M5 | Pending |
| F-14 | MCP HTTP server | P2 | M5 | Pending |
| F-15 | Agent perceive loop | P0 | M6 | Pending |
| F-16 | Max step limiter | P0 | M10 | Pending |
| F-17 | Kill switch | P0 | M10 | Pending |
| F-18 | Audit log | P0 | M10 | Pending |
| F-19 | Browser open/navigate | P0 | M7 | Pending |
| F-20 | Browser form fill | P0 | M7 | Pending |
| F-21 | Browser screenshot | P1 | M7 | Pending |
| F-22 | File list/read | P0 | M8 | Pending |
| F-23 | File write/move/delete | P0 | M8 | Pending |
| F-24 | Terminal run | P0 | M9 | Pending |
| F-25 | Destructive action confirm | P0 | M10 | Pending |
| F-26 | Config-driven backend swap | P0 | M11 | Pending |
| F-27 | Install script | P0 | M13 | Pending |

---

## 6. Tool Inventory

### System Tools (pacman/yay)
| Tool | Package | Purpose | Wayland Native |
|---|---|---|---|
| grim | `grim` | Screenshot capture | ✅ Yes |
| slurp | `slurp` | Interactive region select | ✅ Yes |
| ydotool | `ydotool` | Mouse/keyboard injection | ✅ Yes (uinput) |
| ydotoold | (part of ydotool) | Input daemon | ✅ Yes |
| wl-copy/paste | `wl-clipboard` | Clipboard operations | ✅ Yes |
| tesseract | `tesseract` | OCR engine | N/A |
| xdg-open | (base system) | Open files with default app | ✅ Yes |

### Python Libraries
| Library | Purpose |
|---|---|
| `mcp` | MCP server/client SDK |
| `anthropic` | Claude API client |
| `google-generativeai` | Gemini API client |
| `ollama` | Ollama Python client |
| `playwright` | Browser automation |
| `pytesseract` | Tesseract Python wrapper |
| `Pillow` | Image processing |
| `pydantic` | Config & schema validation |
| `httpx` | Async HTTP client |
| `rich` | Terminal output formatting |
| `pyyaml` | Config file parsing |
| `pytest` | Test framework |

---

## 7. Dependency Graph

```
M0 (ENV)
  └── M1 (SCREEN)
        └── M3 (OCR)
  └── M2 (INPUT)
  └── M4 (BACKEND)
        └── M5 (MCP) ← requires M1, M2, M3, M4
              └── M6 (LOOP)
                    ├── M7 (BROWSER)
                    ├── M8 (FILES)
                    └── M9 (TERMINAL)
                          └── M10 (SAFETY)
                                └── M11 (MULTI-BACKEND)
                                      └── M12 (INTEGRATION)
                                            └── M13 (RELEASE)
```

Build order is strictly sequential from M0 → M13.
Never start a milestone until all its dependencies pass acceptance criteria.

---

## 8. Risk Register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| ydotool fails to inject on Hyprland | Medium | High | Test early in M0; fallback to `wtype`/`wlrctl` |
| grim needs portal permission | Low | Medium | Configure `xdg-desktop-portal-hyprland` |
| Playwright Wayland rendering issues | Medium | Medium | Use `--ozone-platform=wayland` flag; fallback X11 mode |
| Tesseract accuracy too low | Low | Low | Supplement with AI vision description |
| Ollama model lacks vision support | Medium | Low | Require llava or minicpm-v model |
| Loop runs amok (destroys files) | Medium | High | Implement M10 safety controls before M12 |
| API rate limits during long tasks | Low | Medium | Add exponential backoff in backend adapters |

---

## 9. Definition of Done

A milestone is **Done** when:
1. All listed functions are implemented and callable
2. The corresponding MCP tool registers and responds correctly
3. At least one manual test of the feature passes
4. No new `sudo` requirements introduced
5. Code has been reviewed by Claude Code for quality
6. Audit log records the action when the tool is called

The project is **Release Ready** when:
1. All 13 milestones are Done
2. All 10 system tests pass
3. `install.sh` runs without errors on a fresh CachyOS install
4. CLAUDE.md, README.md, and config.yaml.example are complete and accurate

---

*End of PLAN.md — Next document: PRD.md*
