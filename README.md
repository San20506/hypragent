# HyprAgent

**Native, model-agnostic computer use agent for Hyprland/Wayland.**

HyprAgent exposes full desktop control as MCP tools — works with Claude Code, OpenCode, or any MCP client. No Docker, no sandbox, no XWayland. Runs directly on your live Hyprland/CachyOS desktop.

---

## Features

| Category | Tools |
|----------|-------|
| **Screen** | `take_screenshot` (fullscreen + region), `read_screen_text` (OCR) |
| **Mouse** | `mouse_move`, `mouse_click`, `mouse_drag`, `mouse_scroll` |
| **Keyboard** | `keyboard_type`, `keyboard_press` |
| **Browser** | `browser_open`, `browser_navigate`, `browser_click`, `browser_type`, `browser_scroll`, `browser_get_text` |
| **Files** | `file_list`, `file_read`, `file_write`, `file_move`, `file_delete` |
| **Terminal** | `terminal_run` |

**20 tools total.** All accessible via MCP stdio transport.

**Multi-backend:** Claude, Gemini, Ollama — swap via one config line.

**Safety built-in:** kill switch (Ctrl+C), audit log, destructive action confirmation.

---

## Quick Start

### 1. Install system dependencies

```bash
sudo pacman -S grim slurp ydotool wl-clipboard tesseract tesseract-data-eng
sudo modprobe uinput
sudo usermod -aG input $USER   # log out and back in after this
```

### 2. Install Python tooling

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 3. Clone and set up

```bash
git clone https://github.com/yourname/hypragent
cd hypragent
uv sync
cp config.yaml.example config.yaml
```

### 4. Configure

Edit `config.yaml` and set your backend:

```yaml
backend:
  active: claude   # or gemini / ollama
```

Export your API key:

```bash
export ANTHROPIC_API_KEY=sk-ant-...   # for Claude
export GEMINI_API_KEY=...             # for Gemini
# Ollama needs no key — just run ollama serve
```

### 5. Start services

```bash
systemctl --user enable --now ydotool
uv run playwright install chromium
```

### 6. Add to Claude Code (MCP)

```bash
claude mcp add hypr-agent -- uv run --project /path/to/hypragent hypragent
```

Or run the server directly:

```bash
uv run hypragent
```

---

## Usage

### Via MCP client (Claude Code)

Once added as an MCP server, all 20 tools are available to Claude Code automatically. Example prompts:

```
Take a screenshot and tell me what's on screen
Click on the Firefox icon at position 100, 200
Open https://example.com in the browser and get the page title
Run 'git status' in the terminal and show me the output
```

### Directly in Python

```python
import yaml
from agent.backends import load_backend
from agent.loop import AgentLoop

config = yaml.safe_load(open("config.yaml"))
backend = load_backend(config)
loop = AgentLoop(config, backend)
loop.run("Open a terminal and run 'echo hello world'")
```

Press **Ctrl+C** to stop the agent at any time.

---

## Configuration

See [`config.yaml.example`](config.yaml.example) for all options, and [`CONFIGURATION.md`](docs/CONFIGURATION.md) for detailed documentation.

Key settings:

| Setting | Default | Description |
|---------|---------|-------------|
| `backend.active` | `claude` | AI backend: `claude`, `gemini`, `ollama` |
| `loop.max_steps` | `20` | Max perceive→act cycles before abort |
| `loop.confirm_destructive_actions` | `true` | Prompt before file write/move/delete |
| `loop.kill_switch_key` | `ctrl+shift+escape` | Hotkey to abort agent |

Audit log: `~/.config/hypr-agent/audit.log` (JSON lines, one entry per tool call)

---

## Documentation

| Document | Description |
|----------|-------------|
| [INSTALLATION.md](docs/INSTALLATION.md) | Detailed setup and dependency guide |
| [USAGE.md](docs/USAGE.md) | Commands, workflows, advanced use cases |
| [CONFIGURATION.md](docs/CONFIGURATION.md) | All config options explained |
| [API.md](docs/API.md) | MCP tool reference (inputs, outputs, schemas) |
| [FAQ.md](docs/FAQ.md) | Troubleshooting and common errors |
| [CONTRIBUTING.md](CONTRIBUTING.md) | How to contribute |
| [CHANGELOG.md](CHANGELOG.md) | Version history |
| [SECURITY.md](SECURITY.md) | Vulnerability reporting |

## Suggested Folder Structure

```
hypragent/
├── agent/                    # Agent loop and backend implementations
│   ├── backends/            # Claude, Gemini, Ollama adapters
│   └── loop.py              # Main agent loop (perceive → reason → act)
├── tools/                   # Individual tool implementations
│   ├── screenshot.py        # grim integration
│   ├── ocr.py               # tesseract integration
│   ├── mouse.py             # ydotool mouse control
│   ├── keyboard.py          # ydotool keyboard control
│   ├── browser.py           # Playwright browser automation
│   ├── files.py             # File operations
│   └── terminal.py          # Shell command execution
├── examples/                # Usage examples
│   ├── basic_task.py       # Simple agent task
│   ├── multi_backend.py    # Backend switching example
│   ├── use_tools_directly.py
│   └── config.yaml.minimal # Minimal config
├── tests/                   # Test suite
├── docs/                    # Documentation
│   ├── INSTALLATION.md
│   ├── USAGE.md
│   ├── CONFIGURATION.md
│   ├── API.md
│   ├── FAQ.md
│   └── SECURITY.md
├── mcp_server.py            # MCP stdio server
├── config.yaml.example      # Config template
└── install-deps.sh          # System dependency installer
```

---

## Requirements

- CachyOS / Arch Linux with Hyprland
- Python 3.11+
- `uv` package manager
- `grim`, `ydotool`, `tesseract`, `wl-clipboard` (system packages)
- Playwright Chromium (installed via `uv run playwright install chromium`)

---

## License

MIT — see [LICENSE](LICENSE).
