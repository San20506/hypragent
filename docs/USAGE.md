# Usage Guide

## Running via Claude Code (MCP)

After adding HyprAgent as an MCP server, all 20 tools are available to Claude Code.

```bash
claude mcp add hypr-agent -- uv run --project /path/to/hypragent hypragent
```

Example prompts in Claude Code:

```
Take a screenshot and tell me what's open on screen.
Move the mouse to 500, 300 and click.
Type "hello world" into the focused window.
Open https://github.com in the browser and get the page title.
List files in ~/Documents.
Run 'git log --oneline -5' and show the output.
```

---

## Running the Agent Loop Directly

```python
import yaml
from agent.backends import load_backend
from agent.loop import AgentLoop

config = yaml.safe_load(open("config.yaml"))
backend = load_backend(config)
loop = AgentLoop(config, backend)

loop.run("Open a terminal and print the current date")
```

The loop runs until the backend signals `end_turn`, `max_steps` is reached, or you press **Ctrl+C**.

---

## Using Individual Tools

Import and call any tool function directly:

```python
# Screenshot
from tools.screenshot import capture_fullscreen, capture_region
b64_png = capture_fullscreen()                     # returns base64 string
b64_region = capture_region(0, 0, 800, 600)       # x, y, width, height

# OCR
from tools.ocr import extract_text_fullscreen, extract_text_from_region
text = extract_text_fullscreen()
text = extract_text_from_region(100, 100, 400, 200)

# Mouse
from tools.mouse import move_mouse, click, drag, scroll
move_mouse(500, 300)
click(500, 300, button="left")
drag(100, 100, 400, 400)
scroll(500, 300, direction="down", amount=3)

# Keyboard
from tools.keyboard import type_text, press_key
type_text("hello world")
press_key("ctrl+c")
press_key("Return")

# Files
from tools.files import file_list, file_read, file_write, file_delete, file_move
entries = file_list("/home/user/Documents")
content = file_read("/home/user/notes.txt")
file_write("/tmp/output.txt", "hello\nworld", confirm=False)
file_move("/tmp/a.txt", "/tmp/b.txt", confirm=False)
file_delete("/tmp/b.txt", confirm=False)

# Terminal
from tools.terminal import terminal_run
result = terminal_run("ls -la ~")
print(result.stdout)
print(result.returncode)
print(result.timed_out)

# Browser
from tools.browser import browser_open, browser_navigate, browser_get_text
browser_open()
browser_navigate("https://example.com")
text = browser_get_text()
```

---

## Stopping the Agent

- **Ctrl+C** — always works; sets the kill flag and exits cleanly.
- **Configured hotkey** — `kill_switch_key` in `config.yaml` (default: `ctrl+shift+escape`).
- **Max steps** — agent stops automatically after `loop.max_steps` cycles.

---

## Inspecting the Audit Log

Every tool call is logged as a JSON line:

```bash
# Stream live
tail -f ~/.config/hypr-agent/audit.log

# Pretty-print last 10 entries
tail -10 ~/.config/hypr-agent/audit.log | python3 -m json.tool

# Filter for a specific tool
grep '"tool": "terminal_run"' ~/.config/hypr-agent/audit.log
```

Each entry contains: `timestamp`, `tool`, `args`, `result` (truncated to 200 chars).

---

## Multi-Backend Switching

Change `backend.active` in `config.yaml` and restart the server:

```yaml
backend:
  active: gemini   # was: claude
```

Or override at runtime:

```python
config["backend"]["active"] = "ollama"
backend = load_backend(config)
```

---

## Advanced: Custom Task Loop

```python
from agent.loop import AgentLoop, _dispatch_tool

# Run a specific tool directly (bypasses agent reasoning)
result = _dispatch_tool(
    "terminal_run",
    {"command": "echo hello"},
    config={"loop": {"confirm_destructive_actions": False}}
)
print(result)  # "hello\n"

# Build a multi-step task
loop = AgentLoop(config, backend)
loop.run("""
    1. Take a screenshot
    2. Read the text on screen using OCR
    3. Write a summary to /tmp/screen-summary.txt
    4. Print 'done' in the terminal
""")
```

---

## Running Tests

```bash
# Non-wayland tests (CI-safe)
uv run pytest tests/ -m "not wayland" -v

# All tests including Wayland (requires live session)
uv run pytest tests/ -v

# Specific test
uv run pytest tests/test_integration.py::test_terminal_run_echo -v
```

---

## Advanced: MCP Server

The MCP server (`mcp_server.py`) exposes all 20 tools over stdio. It's compatible with any MCP client.

### Direct server run

```bash
# Start the server (blocks, Ctrl+C to stop)
uv run hypragent

# Or run the Python module directly
uv run python -m hypragent
```

### Testing MCP communication

You can test the MCP server directly:

```bash
# Send a JSON-RPC initialize request
echo '{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}' | uv run hypragent
```

### MCP client examples

#### Claude Code

```bash
claude mcp add hypr-agent -- uv run --project /path/to/hypragent hypragent

# List available tools
claude mcp list
```

#### OpenCode

Add to your OpenCode MCP configuration:

```json
{
  "mcpServers": {
    "hypr-agent": {
      "command": "uv",
      "args": ["run", "--project", "/path/to/hypragent", "hypragent"]
    }
  }
}
```
