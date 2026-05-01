# HyprAgent

**Native, model-agnostic computer use agent for Hyprland/Wayland.**

HyprAgent exposes full desktop control as MCP tools — works with Claude Code, OpenCode, or any MCP client.

## Quick Start

```bash
# 1. Install dependencies
sudo pacman -S grim slurp ydotool wl-clipboard tesseract tesseract-data-eng
sudo modprobe uinput
sudo usermod -aG input $USER

# 2. Setup
git clone https://github.com/yourname/hypragent
cd hypragent
uv sync
cp config.yaml.example config.yaml

# 3. Add to Claude Code
claude mcp add hypr-agent -- uv run --project $(pwd) hypragent
```

See [README.dev.md](README.dev.md) for full documentation and setup details.

## Documentation
- [Installation Guide](docs/INSTALLATION.md)
- [Usage Guide](docs/USAGE.md)
- [API Reference](docs/API.md)
- [FAQ](docs/FAQ.md)

## License
MIT
