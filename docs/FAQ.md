# FAQ & Troubleshooting

---

## Installation

### `Permission denied` when ydotool tries to inject input

**Cause:** Your user is not in the `input` group, or you haven't re-logged in since being added.

**Fix:**
```bash
sudo usermod -aG input $USER
# Log out and log back in
groups | grep input   # verify
```

Also ensure the `uinput` kernel module is loaded:
```bash
sudo modprobe uinput
lsmod | grep uinput   # should show uinput
```

---

### `ydotool: error: failed to connect to ydotoold`

**Cause:** The ydotool daemon isn't running.

**Fix:**
```bash
systemctl --user start ydotool
systemctl --user status ydotool
```

If the service shows `start-limit-hit`, reset and restart:
```bash
systemctl --user reset-failed ydotool
systemctl --user start ydotool
```

---

### `grim: failed to create screencopy manager`

**Cause:** The `xdg-desktop-portal-hyprland` portal isn't running or isn't authorized.

**Fix:**
```bash
# Ensure the portal is installed
sudo pacman -S xdg-desktop-portal-hyprland

# Restart portals
systemctl --user restart xdg-desktop-portal xdg-desktop-portal-hyprland
```

---

## Hyprland Specifics

### Window focus issues / clicks land on wrong window

**Cause:** Hyprland's focus model differs from X11. The clicked window must be focused.

**Fix:** Use `mouse_click` instead of `mouse_move` + separate click, or add a small delay between move and click in your task.

---

### ydotool doesn't work in certain apps

Some apps (like Electron apps, certain Qt apps) may not respond to ydotool input due to Wayland security restrictions. This is a known limitation of the Wayland protocol, not a HyprAgent bug.

---

## API Keys

### `ANTHROPIC_API_KEY not set`

**Fix:**
```bash
# Add to your shell profile (~/.bashrc or ~/.zshrc)
export ANTHROPIC_API_KEY=sk-ant-...

# Reload
source ~/.bashrc
```

For temporary testing:
```bash
export ANTHROPIC_API_KEY=sk-ant-...
uv run hypragent
```

---

### API key is correct but still fails

- Verify no extra spaces: `echo $ANTHROPIC_API_KEY`
- Check the key hasn't expired
- Ensure you have API credits available

---

### Playwright fails to launch / `browser not found`

**Cause:** Chromium not installed via Playwright.

**Fix:**
```bash
uv run playwright install chromium
```

If Chromium launches but shows a blank screen:
```bash
# Verify Wayland flags are set
uv run python -c "from tools.browser import _ensure_browser; import asyncio; asyncio.run(_ensure_browser())"
```

---

### `ModuleNotFoundError: No module named 'anthropic'`

**Cause:** Python dependencies not installed.

**Fix:**
```bash
uv sync
```

For dev/test dependencies:
```bash
uv sync --extra dev
```

---

## Runtime

### Agent runs too many steps / doesn't stop

Set a lower `max_steps` in `config.yaml`:
```yaml
loop:
  max_steps: 5
```

Or press **Ctrl+C** to stop immediately.

---

### OCR returns garbled text or empty string

- Ensure `tesseract-data-eng` is installed: `pacman -Q tesseract-data-eng`
- OCR works better at higher resolution. Try a smaller region around the text.
- PNG format gives better accuracy than JPEG: `screenshot_format: png`

---

### `keyboard_type` types the wrong characters / skips characters

ydotool type speed may be too fast for some apps. This is a known limitation of `ydotool type --delay` — characters can drop under load. No config workaround in v1.0; fixed in upstream ydotool or use `keyboard_press` for individual keys.

---

### `terminal_run` is blocked unexpectedly

Check if your command contains a substring from the blocklist:
```bash
grep -A5 "command_blocklist" config.yaml
```

To add an exception, you must remove or modify the blocklist entry. **Do not remove safety entries like `rm -rf /`.**

---

### `confirm_destructive_actions` prompts even in scripts

Set it to `false` in your config or pass `confirm=False` to Python tool functions directly:

```python
from tools.files import file_write
file_write("/tmp/out.txt", "data", confirm=False)
```

Or use `_dispatch_tool` with an explicit config:
```python
from agent.loop import _dispatch_tool
_dispatch_tool("file_write", {"path": "/tmp/out.txt", "content": "data"},
               config={"loop": {"confirm_destructive_actions": False}})
```

---

### Gemini shows `FutureWarning: Call to deprecated ...`

This is a known issue with `google-generativeai` 0.8.6. The SDK is deprecated upstream. Migration to `google-genai` is planned for v1.1. The warning does not affect functionality.

---

### MCP server not found by Claude Code

Verify the server is registered:
```bash
claude mcp list
```

Re-add if missing:
```bash
claude mcp add hypr-agent -- uv run --project /path/to/hypragent hypragent
```

Test the server manually:
```bash
cd /path/to/hypragent
uv run hypragent   # should start without errors
```

---

## Logs

### Where is the audit log?

```
~/.config/hypr-agent/audit.log
```

```bash
tail -20 ~/.config/hypr-agent/audit.log | python3 -m json.tool
```

### How do I clear the audit log?

```bash
> ~/.config/hypr-agent/audit.log   # truncate (bash redirect)
```

---

## Still stuck?

Open an issue at [github.com/yourname/hypragent/issues](../../issues) with:
- Your OS version: `uname -a`
- Python version: `uv run python --version`
- ydotool version: `ydotool --version`
- The full error output
