# PRD.md — Product Requirements Document
## HyprAgent: Model-Agnostic Computer Use Agent for Hyprland/Wayland
> Version: 1.0 | Status: Draft | Date: 2026-04-02
> Owner: User | Builder: Claude Code

---

## Table of Contents
1. [Executive Summary](#1-executive-summary)
2. [Problem Statement](#2-problem-statement)
3. [Goals & Non-Goals](#3-goals--non-goals)
4. [User Personas](#4-user-personas)
5. [Functional Requirements](#5-functional-requirements)
6. [Technical Requirements](#6-technical-requirements)
7. [System Architecture](#7-system-architecture)
8. [MCP Tool Specifications](#8-mcp-tool-specifications)
9. [Backend Adapter Contract](#9-backend-adapter-contract)
10. [Configuration Schema](#10-configuration-schema)
11. [Safety & Security Requirements](#11-safety--security-requirements)
12. [Performance Requirements](#12-performance-requirements)
13. [Constraints & Assumptions](#13-constraints--assumptions)
14. [Acceptance Criteria](#14-acceptance-criteria)
15. [Out of Scope (v1)](#15-out-of-scope-v1)

---

## 1. Executive Summary

HyprAgent is a locally-running, model-agnostic AI computer use agent for CachyOS with the Hyprland compositor. It enables any MCP-compatible AI client (Claude Code, OpenCode, or custom) to see the user's screen, control mouse and keyboard, read screen content via OCR, automate browsers, manage files, and run terminal commands — all natively on Wayland without requiring Docker, virtual machines, or macOS.

The system is designed to be the Linux/Hyprland equivalent of Anthropic's Claude Computer Use feature, extended with a swappable AI backend so users can run it with Claude, Gemini, or local LLMs interchangeably via a single configuration change.

---

## 2. Problem Statement

### Current Situation
Anthropic's Computer Use feature is designed and tested primarily for macOS. Linux users on Wayland — particularly those running cutting-edge compositors like Hyprland — face multiple barriers:

- macOS-specific APIs (`CGWindowListCreateImage`, `CGEvent`) have no Wayland equivalents
- Traditional Linux input injection tools (`xdotool`, `pyautogui`) require X11 and **do not work on Wayland**
- Screenshot tools that require X11 (`scrot`, `import`) fail silently on pure Wayland sessions
- Anthropic's official `computer-use-demo` runs inside a Docker container with a virtual X11 desktop — bypassing rather than solving the Wayland problem
- Existing community ports are either macOS-only, X11-only, or cloud-sandboxed

### What We Are Solving
A native, first-class computer use agent that works **on the user's actual Hyprland desktop** using Wayland-native tools and protocols, with the AI model being freely swappable based on cost, capability, or availability.

---

## 3. Goals & Non-Goals

### Goals (v1)
- ✅ Full screen capture on Wayland via `grim`
- ✅ Native mouse and keyboard injection via `ydotool` (no XWayland)
- ✅ OCR-based screen reading via `tesseract`
- ✅ Browser automation via `playwright` (Wayland mode)
- ✅ File system operations with safety confirmations
- ✅ Terminal command execution with output capture
- ✅ MCP server exposing all capabilities as tools
- ✅ Swappable AI backends: Claude, Gemini, Ollama
- ✅ Configurable agent loop with safety controls
- ✅ Append-only audit log of all actions

### Non-Goals (v1)
- ❌ GUI application (CLI/MCP only in v1)
- ❌ Cloud deployment or remote agent
- ❌ Multi-user or multi-session support
- ❌ Windows or macOS support
- ❌ Voice command interface (planned v1.1)
- ❌ Multi-monitor support (planned v1.1)
- ❌ Mobile device control

---

## 4. User Personas

### Primary: Power Linux User — "The Automator"
- Runs CachyOS with Hyprland as daily driver
- Uses Claude Code for development work
- Wants to automate repetitive desktop tasks: filling forms, managing files, running scripts
- Technically capable but does not want to maintain complex infrastructure
- Values: speed, native feel, no Docker overhead, privacy (local LLM option)

### Secondary: Developer — "The Builder"
- Building on top of HyprAgent to create custom automation pipelines
- Needs stable MCP tool API and clear documentation
- Values: predictable interfaces, extensibility, model flexibility

---

## 5. Functional Requirements

### FR-01 — Screen Capture
**Priority:** P0 (Must Have)

The system SHALL be able to:
- Capture the full Wayland display as a PNG image
- Capture a rectangular region of the display specified by (x, y, width, height)
- Return the captured image as a base64-encoded PNG string for passing to AI backends
- Save screenshots to a configurable output directory with timestamp filenames

The system SHALL NOT:
- Require X11 or XWayland to be running
- Require elevated privileges (sudo) for screen capture
- Depend on proprietary display server extensions

Implementation: `grim` (Wayland screenshot utility)

---

### FR-02 — Mouse Control
**Priority:** P0 (Must Have)

The system SHALL be able to:
- Move the mouse cursor to absolute screen coordinates (x, y)
- Move the mouse cursor by a relative offset (dx, dy)
- Perform left, right, and middle button clicks at specified coordinates
- Perform double-clicks
- Perform click-and-drag between two coordinate pairs
- Scroll up, down, left, and right by a specified number of units

The system SHALL NOT:
- Require X11 for input injection
- Fail silently — all input errors must surface as exceptions

Implementation: `ydotool` with `ydotoold` daemon via `uinput`

---

### FR-03 — Keyboard Input
**Priority:** P0 (Must Have)

The system SHALL be able to:
- Type arbitrary Unicode text strings into the currently focused window
- Press individual keys by name (e.g., `Return`, `Escape`, `Tab`, `BackSpace`)
- Press key combinations / hotkeys (e.g., `ctrl+c`, `alt+F4`, `super+Return`)
- Insert clipboard content via paste hotkey

The system SHALL NOT:
- Drop characters on fast typing (must add configurable delay between keystrokes if needed)
- Require XWayland

Implementation: `ydotool key` and `ydotool type`

---

### FR-04 — OCR / Screen Reading
**Priority:** P0 (Must Have)

The system SHALL be able to:
- Extract all readable text from a full-screen screenshot
- Extract text from a specific screen region
- Return extracted text as a plain UTF-8 string
- Pass extracted text to the AI backend as additional context alongside the visual screenshot

Implementation: `tesseract-ocr` via `pytesseract` Python wrapper

---

### FR-05 — Browser Automation
**Priority:** P0 (Must Have)

The system SHALL be able to:
- Open a new browser window and navigate to a URL
- Navigate to a new URL in the current browser window
- Click on elements identified by CSS selector or XPath
- Type text into input fields
- Scroll the page vertically and horizontally
- Extract visible text content from a page or element
- Take a screenshot of the current browser viewport
- Close the browser

The system SHALL:
- Run Chromium in Wayland-native mode (`--ozone-platform=wayland`)
- Manage a persistent browser session across multiple tool calls within one agent loop

Implementation: `playwright` Python library with Chromium

---

### FR-06 — File Management
**Priority:** P0 (Must Have)

The system SHALL be able to:
- List files and directories at a given path, returning names, sizes, and modification times
- Read the text content of a file, returning it as a UTF-8 string
- Write text content to a file (create or overwrite)
- Move or rename a file or directory
- Delete a file or directory
- Open a file with its default application via `xdg-open`

The system SHALL:
- Prompt for user confirmation before write, move, and delete operations when `confirm_destructive_actions: true`
- Refuse to operate outside configured allowed paths if a path allowlist is set
- Handle binary files gracefully (report as non-text, do not corrupt)

---

### FR-07 — Terminal Command Execution
**Priority:** P0 (Must Have)

The system SHALL be able to:
- Execute an arbitrary shell command and capture its stdout, stderr, and return code
- Enforce a configurable timeout on command execution
- Return a structured result object: `{ command, stdout, stderr, returncode, timed_out, duration_ms }`
- Run commands in a configurable working directory

The system SHALL:
- Never use `shell=True` with unsanitized input — always use argument list form
- Enforce a configurable blocklist of forbidden commands/prefixes
- Log every command execution to the audit log before executing

The system SHALL NOT:
- Allow infinite-running commands (timeout is mandatory)
- Run commands as root

---

### FR-08 — Model-Agnostic AI Backend
**Priority:** P0 (Must Have)

The system SHALL:
- Define a `BackendAdapter` abstract base class with a stable interface
- Implement concrete adapters for: Claude (Anthropic API), Gemini (Google AI), Ollama (local)
- Allow switching the active backend by changing one line in `config.yaml`
- Require no code changes to switch backends
- Support vision (image input) for all three adapters (using vision-capable models)
- Expose the active backend name and model via a `/status` endpoint

The `BackendAdapter` interface SHALL define:
- `send_message(messages, tools, images) → AgentResponse`
- `get_model_name() → str`
- `supports_vision() → bool`
- `get_backend_name() → str`

---

### FR-09 — MCP Server
**Priority:** P0 (Must Have)

The system SHALL:
- Implement the MCP (Model Context Protocol) server specification
- Register and expose all tools from FR-01 through FR-07 as MCP tools
- Support MCP stdio transport (primary — compatible with Claude Code)
- Support MCP HTTP transport (secondary — compatible with OpenCode and web clients)
- Respond to `tools/list` with correct JSON Schema for all tools
- Respond to `tools/call` by routing to the correct tool implementation and returning results

The MCP server SHALL:
- Start within 2 seconds of launch
- Handle tool call errors gracefully and return structured error responses
- Never crash on malformed input — log and return error

---

### FR-10 — Agent Loop
**Priority:** P0 (Must Have)

The system SHALL implement an autonomous agent loop:
1. Capture screenshot
2. Run OCR on screenshot
3. Compose message: task description + screenshot (base64) + OCR text + action history
4. Send to active AI backend
5. Parse response for tool calls
6. Execute tool calls sequentially
7. Append results to history
8. Check termination conditions
9. Repeat

Termination conditions:
- AI backend signals task complete
- Max step count reached (configurable, default: 20)
- Kill switch triggered
- Unrecoverable error

The loop SHALL:
- Emit a progress event after each step (for UI integration)
- Write every step summary to audit log
- Be interruptible at any step boundary via kill switch

---

## 6. Technical Requirements

### TR-01 — Operating System
- CachyOS (Arch Linux base), kernel 6.x
- Hyprland compositor, Wayland session
- No XWayland dependency for any core functionality

### TR-02 — System Dependencies

| Package | Install Command | Version |
|---|---|---|
| grim | `sudo pacman -S grim` | ≥1.4 |
| slurp | `sudo pacman -S slurp` | ≥1.4 |
| ydotool | `sudo pacman -S ydotool` | ≥1.0 |
| wl-clipboard | `sudo pacman -S wl-clipboard` | ≥2.0 |
| tesseract | `sudo pacman -S tesseract tesseract-data-eng` | ≥5.0 |
| python | `sudo pacman -S python` | ≥3.11 |
| uv | `curl -LsSf https://astral.sh/uv/install.sh \| sh` | latest |

### TR-03 — Python Dependencies

| Library | Version | Purpose |
|---|---|---|
| mcp | ≥1.0 | MCP server SDK |
| anthropic | ≥0.40 | Claude API |
| google-generativeai | ≥0.8 | Gemini API |
| ollama | ≥0.4 | Ollama client |
| playwright | ≥1.45 | Browser automation |
| pytesseract | ≥0.3 | OCR wrapper |
| Pillow | ≥10.0 | Image processing |
| pydantic | ≥2.0 | Data validation |
| pyyaml | ≥6.0 | Config parsing |
| rich | ≥13.0 | Terminal UI |
| httpx | ≥0.27 | HTTP client |
| pytest | ≥8.0 | Testing |

### TR-04 — Kernel / System Config

| Requirement | Command | Purpose |
|---|---|---|
| uinput module | `sudo modprobe uinput` | ydotool input injection |
| uinput on boot | `/etc/modules-load.d/uinput.conf` | Persist across reboots |
| input group | `sudo usermod -aG input $USER` | ydotool socket access |
| ydotoold service | `systemctl --user enable --now ydotoold` | Input daemon |

### TR-05 — Project Layout

```
hypr-agent/
├── config.yaml              # Active config (gitignored)
├── config.yaml.example      # Template with all options documented
├── mcp_server.py            # Entry point: MCP server
├── install.sh               # One-command setup for CachyOS
├── pyproject.toml           # Python project metadata & dependencies
├── CLAUDE.md                # Claude Code agent instructions
├── README.md                # Human quickstart guide
├── agent/
│   ├── __init__.py
│   ├── loop.py              # Agent perceive→reason→act loop
│   ├── models.py            # Pydantic models (AgentResponse, ToolResult, etc.)
│   ├── config.py            # Config loader and validator
│   ├── audit.py             # Append-only audit logger
│   └── backends/
│       ├── __init__.py
│       ├── base.py          # BackendAdapter ABC
│       ├── claude.py        # Anthropic Claude adapter
│       ├── gemini.py        # Google Gemini adapter
│       └── ollama.py        # Ollama local LLM adapter
├── tools/
│   ├── __init__.py
│   ├── registry.py          # Tool registry — maps tool names to callables
│   ├── screenshot.py        # FR-01: Screen capture
│   ├── mouse.py             # FR-02: Mouse control
│   ├── keyboard.py          # FR-03: Keyboard input
│   ├── ocr.py               # FR-04: OCR / screen reading
│   ├── browser.py           # FR-05: Browser automation
│   ├── files.py             # FR-06: File management
│   └── terminal.py          # FR-07: Terminal execution
├── logs/
│   └── audit.log            # Append-only action log
└── tests/
    ├── test_screenshot.py
    ├── test_mouse.py
    ├── test_keyboard.py
    ├── test_ocr.py
    ├── test_browser.py
    ├── test_files.py
    ├── test_terminal.py
    └── test_mcp_server.py
```

---

## 7. System Architecture

### Data Flow — Single Agent Step

```
User / MCP Client
      │
      │ tools/call: { name: "take_screenshot" }
      ▼
MCP Server (mcp_server.py)
      │
      │ routes to tool registry
      ▼
tools/screenshot.py
      │
      │ subprocess: grim -t png -
      ▼
PNG bytes → base64 string
      │
      │ returned as MCP tool result
      ▼
MCP Client / Agent Loop
      │
      │ + task description + OCR text
      ▼
BackendAdapter.send_message(messages, tools, images)
      │
      │ HTTP POST to AI API
      ▼
AI Response { tool_calls: [...] }
      │
      │ loop.py parses tool calls
      ▼
Tool Execution (mouse/keyboard/browser/files/terminal)
      │
      │ Result appended to history
      ▼
audit.py.log(action, result, timestamp)
```

---

## 8. MCP Tool Specifications

All tools follow MCP JSON Schema specification. Input validation via Pydantic.

### take_screenshot
```json
{
  "name": "take_screenshot",
  "description": "Capture the current Wayland display as a PNG image. Returns base64-encoded PNG.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "region": {
        "type": "object",
        "description": "Optional screen region. If omitted, captures full screen.",
        "properties": {
          "x": {"type": "integer", "description": "Left edge in pixels"},
          "y": {"type": "integer", "description": "Top edge in pixels"},
          "width": {"type": "integer", "description": "Width in pixels"},
          "height": {"type": "integer", "description": "Height in pixels"}
        },
        "required": ["x", "y", "width", "height"]
      }
    }
  }
}
```

### mouse_click
```json
{
  "name": "mouse_click",
  "description": "Move the mouse to coordinates and click.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "x": {"type": "integer", "description": "X coordinate"},
      "y": {"type": "integer", "description": "Y coordinate"},
      "button": {"type": "string", "enum": ["left", "right", "middle"], "default": "left"},
      "double": {"type": "boolean", "default": false, "description": "Double-click if true"}
    },
    "required": ["x", "y"]
  }
}
```

### keyboard_type
```json
{
  "name": "keyboard_type",
  "description": "Type a string of text into the currently focused window.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "text": {"type": "string", "description": "Text to type"},
      "delay_ms": {"type": "integer", "default": 12, "description": "Delay between keystrokes in ms"}
    },
    "required": ["text"]
  }
}
```

### keyboard_press
```json
{
  "name": "keyboard_press",
  "description": "Press a key or key combination.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "keys": {"type": "string", "description": "Key or combo, e.g. 'Return', 'ctrl+c', 'alt+F4'"}
    },
    "required": ["keys"]
  }
}
```

### read_screen_text
```json
{
  "name": "read_screen_text",
  "description": "Extract text from screen using OCR. Returns plain text string.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "region": {
        "type": "object",
        "description": "Optional region. If omitted, OCR runs on full screen.",
        "properties": {
          "x": {"type": "integer"}, "y": {"type": "integer"},
          "width": {"type": "integer"}, "height": {"type": "integer"}
        }
      }
    }
  }
}
```

### terminal_run
```json
{
  "name": "terminal_run",
  "description": "Execute a shell command and return stdout, stderr, and return code.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "command": {"type": "string", "description": "Command and arguments as a string"},
      "cwd": {"type": "string", "description": "Working directory (optional)"},
      "timeout": {"type": "integer", "default": 30, "description": "Timeout in seconds"}
    },
    "required": ["command"]
  }
}
```

### file_read
```json
{
  "name": "file_read",
  "description": "Read the text content of a file.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "path": {"type": "string", "description": "Absolute or relative file path"}
    },
    "required": ["path"]
  }
}
```

### file_write
```json
{
  "name": "file_write",
  "description": "Write text content to a file.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "path": {"type": "string"},
      "content": {"type": "string"},
      "confirm": {"type": "boolean", "default": true}
    },
    "required": ["path", "content"]
  }
}
```

---

## 9. Backend Adapter Contract

All AI backends MUST implement the following Python interface:

```
class BackendAdapter(ABC):

    @abstractmethod
    def send_message(
        self,
        messages: list[dict],
        tools: list[dict],
        images: list[str]          # list of base64 PNG strings
    ) -> AgentResponse:
        """
        Send conversation to AI backend.
        Returns structured response with text and/or tool calls.
        """

    @abstractmethod
    def get_model_name(self) -> str:
        """Return the model identifier string."""

    @abstractmethod
    def supports_vision(self) -> bool:
        """Return True if this backend can process image inputs."""

    @abstractmethod
    def get_backend_name(self) -> str:
        """Return the backend name: 'claude', 'gemini', or 'ollama'."""
```

`AgentResponse` model:
```
class AgentResponse(BaseModel):
    text: str | None
    tool_calls: list[ToolCall]
    finish_reason: str    # "tool_use" | "end_turn" | "max_tokens" | "error"
    backend: str
    model: str
    usage: dict           # tokens/cost info if available
```

---

## 10. Configuration Schema

Full `config.yaml` specification:

```yaml
# HyprAgent Configuration
# Copy this file to config.yaml and fill in your values.

backend:
  active: claude          # Options: claude | gemini | ollama

  claude:
    model: claude-sonnet-4-5
    api_key_env: ANTHROPIC_API_KEY
    max_tokens: 4096

  gemini:
    model: gemini-2.5-flash
    api_key_env: GEMINI_API_KEY
    max_tokens: 4096

  ollama:
    endpoint: http://localhost:11434
    model: llava
    max_tokens: 4096

loop:
  max_steps: 20
  screenshot_on_every_step: true
  ocr_on_every_step: true
  step_delay_ms: 500
  confirm_destructive_actions: true
  kill_switch_key: ctrl+shift+escape

tools:
  terminal:
    timeout_seconds: 30
    blocked_commands:
      - "rm -rf /"
      - "dd if="
      - "mkfs"
    allowed_cwd: null           # null = unrestricted

  files:
    allowed_paths: null         # null = unrestricted
    confirm_delete: true
    confirm_overwrite: true

  browser:
    browser: chromium
    headless: false
    wayland: true

  screenshot:
    output_dir: ./logs/screenshots
    format: png
    quality: 95

  ocr:
    language: eng
    psm: 3                      # Tesseract page segmentation mode

logging:
  audit_log: ./logs/audit.log
  level: INFO
  include_screenshots_in_log: false

mcp:
  transport: stdio              # Options: stdio | http
  http_port: 8765               # Only used if transport: http
```

---

## 11. Safety & Security Requirements

### SR-01 — Destructive Action Confirmation
All file write, move, and delete operations MUST prompt for user confirmation when `confirm_destructive_actions: true`. The prompt must display the exact operation and target before proceeding.

### SR-02 — Terminal Command Blocklist
Commands matching any pattern in `blocked_commands` MUST be rejected before execution. The rejection must be logged.

### SR-03 — Loop Kill Switch
The agent loop MUST be terminable at any step boundary by:
- The configured kill switch hotkey
- Sending `SIGINT` (Ctrl+C) to the process
- Setting a kill flag via MCP tool `agent_stop`

### SR-04 — Audit Log
Every action taken by the agent MUST be written to the append-only audit log before execution. Log entry format:
```json
{
  "timestamp": "2026-04-02T12:34:56.789Z",
  "step": 3,
  "tool": "terminal_run",
  "input": { "command": "ls -la /home/user" },
  "result": { "returncode": 0, "stdout": "..." },
  "backend": "claude",
  "task_id": "uuid-here"
}
```

### SR-05 — No Root Execution
The agent process MUST NOT run as root. All tools MUST function under a normal user account. System dependency setup (modprobe, usermod) is a one-time manual step documented in the install guide, not performed at runtime.

### SR-06 — Credential Handling
API keys MUST be read from environment variables only. They MUST NOT be hardcoded, logged, or included in screenshots passed to AI backends.

---

## 12. Performance Requirements

| Metric | Target |
|---|---|
| Screenshot capture latency | < 500ms |
| OCR on full 1080p screen | < 3 seconds |
| Mouse move + click latency | < 200ms |
| Keyboard type throughput | ≥ 50 chars/sec |
| MCP server startup time | < 2 seconds |
| Browser page load (local) | < 5 seconds |
| Agent loop step time (no AI) | < 1 second |
| Agent loop step time (with AI) | < 10 seconds (network dependent) |

---

## 13. Constraints & Assumptions

### Constraints
- Hyprland compositor must be running (no fallback to other compositors in v1)
- `ydotoold` daemon must be running before any input injection
- `uinput` kernel module must be loaded
- User must be in the `input` group
- Internet connection required for Claude and Gemini backends
- Ollama must be locally running for ollama backend

### Assumptions
- User has a single monitor (multi-monitor support in v1.1)
- Display resolution is ≥ 1080p (OCR quality degrades below this)
- Claude Code is installed and functional for MCP client usage
- Python 3.11 or higher is available on the system

---

## 14. Acceptance Criteria

### v1 Release Acceptance
The product is accepted when ALL of the following pass:

| ID | Test | Pass Condition |
|---|---|---|
| AC-01 | Screenshot capture | Returns valid PNG base64 within 500ms |
| AC-02 | Mouse click accuracy | Clicks land within 5px of target |
| AC-03 | Keyboard typing | 100-char string typed with zero errors |
| AC-04 | OCR accuracy | Extracts ≥90% of visible terminal text correctly |
| AC-05 | Browser form fill | Fills and submits a web form successfully |
| AC-06 | File read/write | Round-trip preserves UTF-8 content exactly |
| AC-07 | Terminal execution | `ls -la` returns correct output; blocked command rejected |
| AC-08 | Kill switch | Loop terminates within 1 second of kill switch |
| AC-09 | Audit log | Every action appears in audit.log with timestamp |
| AC-10 | Backend swap | Changing `config.yaml` `active` field switches backend with no code change |
| AC-11 | MCP registration | `claude mcp add` succeeds; `tools/list` returns all tools |
| AC-12 | End-to-end task | Agent completes: open Firefox → navigate to github.com → search "hyprland" |
| AC-13 | No sudo at runtime | All AC-01 through AC-12 pass without sudo |

---

## 15. Out of Scope (v1)

The following are explicitly deferred to future versions:

| Feature | Target Version |
|---|---|
| Multi-monitor support | v1.1 |
| Voice command input | v1.1 |
| GUI dashboard | v1.2 |
| Task queue / batch mode | v1.1 |
| Plugin system for custom tools | v1.2 |
| Notification on task completion | v1.1 |
| Recording/replay of agent sessions | v2.0 |
| Remote agent (cloud-hosted) | v2.0 |
| Windows / macOS support | Not planned |
| Mobile support | Not planned |

---

*End of PRD.md — Next document: CLAUDE.md*
