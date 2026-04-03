# CLAUDE.md — Claude Code Agent Instructions
## HyprAgent: Model-Agnostic Computer Use Agent for Hyprland/Wayland

> This file is read automatically by Claude Code when working in this repository.
> It tells Claude Code exactly how to build, test, and reason about this project.

---

## Project Identity

**What this is:** A native computer use agent for CachyOS + Hyprland (Wayland). It lets AI models control the desktop by taking screenshots, moving the mouse, typing, reading the screen via OCR, automating browsers, managing files, and running terminal commands.

**What makes it different:** It runs natively on Wayland (no Docker, no XWayland, no virtual machine). All AI backends (Claude, Gemini, Ollama) are swappable via one config line.

**Primary reference documents:**
- `PLAN.md` — Full milestone map and build order (follow this strictly)
- `PRD.md` — Product requirements, tool schemas, acceptance criteria
- `config.yaml.example` — All configuration options with documentation

---

## Non-Negotiable Rules

These rules apply to every file Claude Code touches in this project. No exceptions.

1. **Never ask to run commands with sudo at runtime.** System setup (modprobe, usermod) is done once manually by the user. All runtime code runs as normal user.

2. **Never hardcode API keys, tokens, or secrets.** Always read from environment variables. Reference the env var name in `config.yaml`, never the value.

3. **Never use `shell=True`** in subprocess calls with user-provided or AI-generated input. Always use argument list form.

4. **Never use X11 tools.** No `xdotool`, `xdg-screensaver`, `xrandr`, `scrot`, `import` (ImageMagick), or any tool requiring `DISPLAY` env var. Wayland-native only.

5. **Never skip writing to the audit log.** Every tool execution — success or failure — must be logged before the result is returned.

6. **Never generate code without a matching milestone.** Check `PLAN.md` to confirm the milestone exists before implementing a feature. Do not gold-plate or add features not in the milestone.

7. **Always validate config against the Pydantic schema** before passing values to tools or backends.

8. **Always write tests alongside new tool implementations.** A tool without a test in `tests/` is not complete.

---

## Build Order

Follow this exact order. Never skip a milestone. Never work on a later milestone until the current one passes its acceptance criteria.

```
M0 (ENV)  →  M1 (SCREEN)  →  M2 (INPUT)  →  M3 (OCR)  →  M4 (BACKEND)
  →  M5 (MCP)  →  M6 (LOOP)  →  M7 (BROWSER)  →  M8 (FILES)
  →  M9 (TERMINAL)  →  M10 (SAFETY)  →  M11 (MULTI-BACKEND)
  →  M12 (INTEGRATION)  →  M13 (RELEASE)
```

Before starting any milestone, state which milestone you are working on and what its acceptance criteria are.

---

## System Architecture Quick Reference

```
mcp_server.py          ← Entry point. Start here.
agent/
  loop.py              ← Perceive → Reason → Act cycle
  config.py            ← Loads and validates config.yaml
  audit.py             ← Append-only action logger
  models.py            ← Pydantic models for all data structures
  backends/
    base.py            ← BackendAdapter ABC (never modify interface once set)
    claude.py          ← Anthropic API adapter
    gemini.py          ← Google Generative AI adapter
    ollama.py          ← Ollama local adapter
tools/
  registry.py          ← Maps tool name strings to callable functions
  screenshot.py        ← grim-based screen capture
  mouse.py             ← ydotool mouse injection
  keyboard.py          ← ydotool keyboard injection
  ocr.py               ← tesseract OCR wrapper
  browser.py           ← playwright browser automation
  files.py             ← file system operations
  terminal.py          ← subprocess command execution
```

---

## Wayland-Specific Knowledge

This is critical context. Get these wrong and nothing works.

### Screenshot
- Use `grim` — this is the correct Wayland tool
- Command: `grim -t png -` (outputs PNG to stdout)
- For region capture: `grim -g "x,y wxh" -t png -`
- Do NOT use: `scrot`, `import`, `gnome-screenshot`, `xwd`
- `WAYLAND_DISPLAY` must be set (usually `wayland-1`) — check with `echo $WAYLAND_DISPLAY`

### Mouse & Keyboard Injection
- Use `ydotool` — this is the correct Wayland tool
- Requires `ydotoold` daemon running: `systemctl --user status ydotoold`
- Requires user in `input` group: `groups | grep input`
- Requires `uinput` module: `lsmod | grep uinput`
- Socket path: usually `/run/user/1000/.ydotool_socket` — set `YDOTOOL_SOCKET` if different
- Commands:
  - Move mouse: `ydotool mousemove --absolute -x 100 -y 200`
  - Click: `ydotool click 0x40` (left=0x40, right=0x41, middle=0x42)
  - Type text: `ydotool type --delay 12 "hello world"`
  - Press key: `ydotool key ctrl+c`
- Do NOT use: `xdotool`, `pyautogui`, `pynput` (all require X11)

### Clipboard
- Read: `wl-paste`
- Write: `echo "text" | wl-copy`
- Do NOT use: `xclip`, `xsel`, `pyperclip` default backend

### Browser (Playwright on Wayland)
- Must pass `--ozone-platform=wayland` to Chromium
- In playwright Python: set `chromium_sandbox=False` if running in restricted env
- Test Wayland mode: `chromium --ozone-platform=wayland`

---

## Common Failure Modes & Fixes

| Symptom | Likely Cause | Fix |
|---|---|---|
| `ydotool: failed to connect to ydotoold` | Daemon not running | `systemctl --user start ydotoold` |
| `ydotool: permission denied` | Not in input group | `sudo usermod -aG input $USER` then re-login |
| `grim: failed to create screencopy manager` | No portal / wrong env | Check `WAYLAND_DISPLAY` is set |
| `tesseract: command not found` | Not installed | `sudo pacman -S tesseract tesseract-data-eng` |
| `playwright: executable not found` | Not installed | `playwright install chromium` |
| `ModuleNotFoundError: mcp` | Not installed | `uv add mcp` |
| Screenshot is black | grim needs compositor permission | Try `grim -o <output-name>` or check portal |

---

## BackendAdapter Interface (Frozen)

Once `agent/backends/base.py` is implemented, this interface is FROZEN. Do not change method signatures without updating ALL adapters and ALL callers.

```python
class BackendAdapter(ABC):
    @abstractmethod
    def send_message(
        self,
        messages: list[dict],
        tools: list[dict],
        images: list[str],          # base64 PNG strings
    ) -> AgentResponse: ...

    @abstractmethod
    def get_model_name(self) -> str: ...

    @abstractmethod
    def supports_vision(self) -> bool: ...

    @abstractmethod
    def get_backend_name(self) -> str: ...
```

`AgentResponse` (from `agent/models.py`):
```python
class AgentResponse(BaseModel):
    text: str | None
    tool_calls: list[ToolCall]
    finish_reason: str      # "tool_use" | "end_turn" | "max_tokens" | "error"
    backend: str
    model: str
    usage: dict
```

---

## MCP Server Conventions

- Use the official `mcp` Python SDK from Anthropic
- Transport: stdio by default (compatible with `claude mcp add`)
- Every tool MUST have a JSON Schema `inputSchema`
- Tool names use `snake_case`
- Tool descriptions must be ≥ 1 complete sentence explaining what the tool does and what it returns
- Error responses MUST be structured `{"error": {"code": str, "message": str}}` — never raise unhandled exceptions

To test MCP locally:
```bash
# Run MCP server
uv run python mcp_server.py

# In another terminal, add to Claude Code
claude mcp add hypr-agent -- uv run python /path/to/mcp_server.py

# Verify
claude mcp list
```

---

## Audit Log Format

Every tool call must produce one log entry. Use `agent/audit.py`.

Required fields:
```json
{
  "timestamp": "ISO8601",
  "task_id": "uuid4",
  "step": 0,
  "tool": "tool_name",
  "input": {},
  "result": {},
  "success": true,
  "duration_ms": 0,
  "backend": "claude | gemini | ollama | none"
}
```

Log path: `./logs/audit.log` (one JSON object per line, newline-delimited).

---

## Config Loading

Config is always loaded at startup from `config.yaml`. The Pydantic model in `agent/config.py` validates it. If config is invalid, exit immediately with a clear error message — never use defaults silently for security-relevant settings (API key env var names, blocked commands).

Env var pattern:
```python
import os
api_key = os.environ.get(config.backend.claude.api_key_env)
if not api_key:
    raise EnvironmentError(f"Missing env var: {config.backend.claude.api_key_env}")
```

---

## Testing Conventions

- Test file: `tests/test_<module>.py` for each `tools/<module>.py`
- Use `pytest`
- Mock subprocess calls for unit tests — do not require `grim`/`ydotool` for unit tests
- Mark integration tests with `@pytest.mark.integration` — these require real Wayland session
- Run unit tests only: `pytest -m "not integration"`
- Run all tests: `pytest`

Example mock pattern for screenshot tests:
```python
from unittest.mock import patch, MagicMock

def test_capture_fullscreen_returns_base64(tmp_path):
    fake_png = b'\x89PNG\r\n...'  # minimal PNG bytes
    with patch('subprocess.run') as mock_run:
        mock_run.return_value = MagicMock(stdout=fake_png, returncode=0)
        result = capture_fullscreen()
        assert isinstance(result, str)
        assert len(result) > 0
```

---

## How to Start a New Work Session

When Claude Code picks this project up fresh, follow this sequence:

1. Read `PLAN.md` — identify the current milestone (look for first `Pending` milestone)
2. Read `PRD.md` section matching that milestone for full spec
3. Read `CLAUDE.md` (this file) for rules and conventions
4. Check if `config.yaml` exists; if not, copy from `config.yaml.example` and prompt user to fill in
5. State the milestone, its acceptance criteria, and the files you will create/modify
6. Implement, then verify against acceptance criteria before marking done

---

## Milestone Completion Checklist

Before calling a milestone complete, verify ALL of the following:

- [ ] All functions listed in PLAN.md for this milestone are implemented
- [ ] The MCP tool(s) for this milestone are registered in `tools/registry.py`
- [ ] The MCP tool(s) return correct JSON Schema in `tools/list`
- [ ] Unit tests exist in `tests/`
- [ ] Unit tests pass: `pytest -m "not integration"`
- [ ] Audit log entry is written on every tool call
- [ ] No new `sudo` required at runtime
- [ ] No API keys hardcoded
- [ ] No X11 tools used

---

## Dependency Installation Commands Reference

```bash
# System tools (run once manually)
sudo pacman -S grim slurp ydotool wl-clipboard tesseract tesseract-data-eng

# Enable ydotool
sudo modprobe uinput
echo "uinput" | sudo tee /etc/modules-load.d/uinput.conf
sudo usermod -aG input $USER
# Log out and back in for group change to take effect
systemctl --user enable --now ydotoold

# Python project setup
uv init hypr-agent
cd hypr-agent
uv add mcp anthropic google-generativeai ollama playwright pytesseract Pillow pydantic pyyaml rich httpx
uv add --dev pytest
playwright install chromium

# Verify all tools accessible
grim --version
ydotool --version
tesseract --version
python -c "import playwright; print('playwright ok')"
python -c "import mcp; print('mcp ok')"
```

---

## Glossary

| Term | Meaning |
|---|---|
| MCP | Model Context Protocol — Anthropic's open protocol for AI tool use |
| ydotool | Wayland-native input injection tool using Linux uinput |
| ydotoold | The ydotool daemon that must run before ydotool can inject input |
| uinput | Linux kernel module enabling userspace input device creation |
| grim | Wayland-native screenshot utility for wlroots-based compositors |
| wlroots | The compositor library Hyprland is built on |
| BackendAdapter | The abstract interface all AI backend implementations must satisfy |
| AgentResponse | The structured return type from any BackendAdapter.send_message call |
| Audit log | Append-only NDJSON file recording every action the agent takes |
| stdio transport | MCP communication via stdin/stdout — default for Claude Code |

---

*End of CLAUDE.md*
*This file should be kept up to date as the project evolves.*
*When adding new tools, update the tool list in "System Architecture Quick Reference".*
*When discovering new Wayland failure modes, add them to "Common Failure Modes & Fixes".*
