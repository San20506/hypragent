# Installation Guide

## Prerequisites

HyprAgent requires CachyOS or Arch Linux with a running Hyprland Wayland compositor.

---

## Step 1 — System Packages

```bash
sudo pacman -S grim slurp ydotool wl-clipboard tesseract tesseract-data-eng
```

| Package | Purpose |
|---------|---------|
| `grim` | Wayland-native screenshot capture |
| `slurp` | Interactive screen region selector |
| `ydotool` | Wayland input injection (mouse + keyboard) |
| `wl-clipboard` | Wayland clipboard (`wl-copy` / `wl-paste`) |
| `tesseract` | OCR engine |
| `tesseract-data-eng` | English OCR language data |

---

## Step 2 — Kernel Module for Input Injection

ydotool requires the `uinput` kernel module:

```bash
sudo modprobe uinput
sudo usermod -aG input $USER
```

**Log out and back in** after adding yourself to the `input` group. Verify:

```bash
groups | grep input
```

To persist `uinput` across reboots:

```bash
echo "uinput" | sudo tee /etc/modules-load.d/uinput.conf
```

---

## Step 3 — Python Tooling (uv)

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Verify:

```bash
uv --version   # should print uv 0.x.x
```

---

## Step 4 — Clone and Install

```bash
git clone https://github.com/yourname/hypragent
cd hypragent
uv sync                    # install runtime deps
uv sync --extra dev        # also install pytest (optional)
```

---

## Step 5 — Playwright Browser

```bash
uv run playwright install chromium
```

This installs Chromium under `~/.cache/ms-playwright/`. Required for `browser_*` tools.

---

## Step 6 — Start the ydotool Daemon

```bash
systemctl --user enable --now ydotool
```

Verify it's running:

```bash
systemctl --user status ydotool
```

The socket appears at `/run/user/1000/.ydotool_socket` (replace `1000` with your UID).

---

## Step 7 — Configure

```bash
cp config.yaml.example config.yaml
```

Open `config.yaml` and set:
- `backend.active` — choose `claude`, `gemini`, or `ollama`
- Backend-specific model name and API key environment variable name

Export your API key(s):

```bash
# Claude
export ANTHROPIC_API_KEY=sk-ant-...

# Gemini
export GEMINI_API_KEY=AIza...

# Ollama — no key needed, just run:
ollama serve
ollama pull llava
```

---

## Step 8 — Add to Claude Code (MCP)

```bash
claude mcp add hypr-agent -- uv run --project /path/to/hypragent hypragent
```

Verify the server starts:

```bash
uv run hypragent
# Should start without errors (Ctrl+C to stop)
```

---

## Troubleshooting

See [FAQ.md](FAQ.md) for common install errors.

**Quick checks:**
```bash
# Is ydotool running?
systemctl --user is-active ydotool

# Can grim take a screenshot?
grim /tmp/test.png && echo "OK"

# Is tesseract working?
tesseract --version

# Does the Python environment have all deps?
uv run python -c "import anthropic, pytesseract, playwright; print('OK')"
```
