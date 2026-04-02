# HyprAgent

Native, model-agnostic computer use agent for Hyprland/Wayland. Exposes full desktop control as MCP tools — works with Claude Code, OpenCode, or any MCP client.

## Prerequisites

System packages (CachyOS/Arch):
```bash
sudo pacman -S grim slurp ydotool wl-clipboard tesseract tesseract-data-eng
sudo modprobe uinput
sudo usermod -aG input $USER   # re-login required
```

Python:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## Quick Start

```bash
git clone <repo-url> hypragent
cd hypragent
uv sync
cp config.yaml.example config.yaml
# Edit config.yaml — set backend.active and export your API key
export ANTHROPIC_API_KEY=sk-ant-...

# Start ydotool daemon (input injection)
systemctl --user enable --now ydotool

# Install Playwright browser
uv run playwright install chromium

# Run MCP server
uv run hypragent
```

## MCP Setup (Claude Code)

```bash
claude mcp add hypr-agent -- uv run --project /path/to/hypragent hypragent
```

## Available Tools

`take_screenshot`, `mouse_move`, `mouse_click`, `mouse_drag`, `mouse_scroll`,
`keyboard_type`, `keyboard_press`, `read_screen_text`,
`browser_open`, `browser_navigate`, `browser_click`, `browser_type`, `browser_scroll`, `browser_get_text`,
`file_list`, `file_read`, `file_write`, `file_move`, `file_delete`,
`terminal_run`

## Run Agent Directly

```python
import yaml
from agent.backends import load_backend
from agent.loop import AgentLoop

config = yaml.safe_load(open("config.yaml"))
backend = load_backend(config)
loop = AgentLoop(config, backend)
loop.run("Open a terminal and run 'echo hello'")
```

Press **Ctrl+C** to stop the agent at any time.

## Configuration

See `config.yaml.example` for all options. Key settings:
- `backend.active` — which AI backend to use (claude/gemini/ollama)
- `loop.max_steps` — safety limit on autonomous steps
- `loop.confirm_destructive_actions` — prompt before destructive file/terminal ops
- `loop.kill_switch_key` — keyboard shortcut to abort running agent (Ctrl+C always works)
- Audit log: `~/.config/hypr-agent/audit.log` — JSON lines, one entry per tool call
