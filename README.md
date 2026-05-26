# HyprAgent

**Native, model-agnostic computer use agent for Hyprland/Wayland.**

HyprAgent exposes full desktop control as MCP tools — works with Claude Code, OpenCode, Hermes Agent, or any MCP client. Now with OpenAI-compatible backend support for OpenCode Go, OpenRouter, and any vLLM/Ollama endpoint.

## Quick Start

```bash
# 1. Install dependencies
sudo pacman -S grim slurp ydotool wl-clipboard tesseract tesseract-data-eng
sudo modprobe uinput
sudo usermod -aG input $USER

# 2. Setup
git clone https://github.com/San20506/hypragent
cd hypragent
uv sync
cp config.yaml.example config.yaml

# 3. Add to Claude Code / Hermes
claude mcp add hypr-agent -- uv run --project $(pwd) hypragent
# or for Hermes:
hermes mcp add hypr-agent --command "uv run --project $(pwd) hypragent"
```

## Backends

| Backend | Provider | Vision | Setup |
|---------|----------|--------|-------|
| `openai_compatible` | OpenCode Go, OpenRouter, vLLM, Ollama, any OpenAI API | Yes | Set `api_key_env` + `base_url` |
| `claude` | Anthropic | Yes | `ANTHROPIC_API_KEY` |
| `gemini` | Google | Yes | `GEMINI_API_KEY` |
| `ollama` | Local | Yes (llava/minicpm-v) | No API key needed |

### Using OpenCode Go (recommended)

```yaml
backend:
  active: openai_compatible
  openai_compatible:
    model: kimi-k2.5              # vision-capable: kimi-k2.5, kimi-k2.6, mimo-v2-omni, glm-5, qwen3.6-plus
    base_url: https://opencode.ai/zen/go/v1
    api_key_env: OPENCODE_GO_API_KEY
```

```bash
export OPENCODE_GO_API_KEY=your_key_here
uv run hypragent
```

## MCP Tools

22 tools exposed: `take_screenshot`, `mouse_move`, `mouse_click`, `mouse_drag`, `mouse_scroll`, `keyboard_type`, `keyboard_press`, `read_screen_text`, `browser_open`, `browser_navigate`, `browser_click`, `browser_type`, `browser_scroll`, `browser_get_text`, `file_list`, `file_read`, `file_write`, `file_move`, `file_delete`, `terminal_run`, `hyprland_workspace_list`, `hyprland_workspace_switch`, `hyprland_clients`, `hyprland_active_window`, `hyprland_focus_window`

See [README.dev.md](README.dev.md) for full documentation.

## License
MIT
