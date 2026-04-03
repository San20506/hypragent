# Configuration Reference

HyprAgent is configured via `config.yaml`. Start from the example:

```bash
cp config.yaml.example config.yaml
```

---

## `backend` — AI Backend

```yaml
backend:
  active: claude   # Required. One of: claude | gemini | ollama
```

### Claude (Anthropic)

```yaml
backend:
  active: claude
  claude:
    model: claude-sonnet-4-6          # Any Claude model ID
    api_key_env: ANTHROPIC_API_KEY    # Name of env var holding the key
```

Export the key:
```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

### Gemini (Google)

```yaml
backend:
  active: gemini
  gemini:
    model: gemini-2.5-flash           # Any Gemini model ID
    api_key_env: GEMINI_API_KEY
```

Export the key:
```bash
export GEMINI_API_KEY=AIza...
```

### Ollama (Local)

```yaml
backend:
  active: ollama
  ollama:
    endpoint: http://localhost:11434  # Ollama server address
    model: llava                      # Must support vision: llava, minicpm-v, bakllava
```

No API key required. Start Ollama and pull a model:
```bash
ollama serve
ollama pull llava
```

Vision support is detected by model name (contains `llava`, `minicpm`, `bakllava`, or `vision`).

---

## `loop` — Agent Loop Behavior

```yaml
loop:
  max_steps: 20                        # Abort after N perceive→act cycles
  screenshot_on_every_step: true       # Capture screen before each reasoning step
  confirm_destructive_actions: true    # Prompt before file write/move/delete/terminal
  kill_switch_key: "ctrl+shift+escape" # Hotkey to abort (Ctrl+C always works)
```

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `max_steps` | int | `20` | Hard limit on autonomous steps |
| `screenshot_on_every_step` | bool | `true` | Include screenshot in every backend call |
| `confirm_destructive_actions` | bool | `true` | Interactive confirmation for destructive tools |
| `kill_switch_key` | string | `ctrl+shift+escape` | Abort hotkey |

**Destructive tools** subject to confirmation: `file_write`, `file_move`, `file_delete`, `terminal_run`.

---

## `safety` — Safety Controls

```yaml
safety:
  command_blocklist:
    - "rm -rf /"
    - "dd if="
    - "mkfs"
    - ":(){:|:&};:"     # fork bomb
  screenshot_format: png
  ocr_language: eng
```

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `command_blocklist` | list[str] | see above | Substrings that cause `terminal_run` to raise |
| `screenshot_format` | string | `png` | Format passed to grim (`png` or `jpeg`) |
| `ocr_language` | string | `eng` | Tesseract language code |

Commands containing any blocklist substring are **always rejected**, regardless of `confirm_destructive_actions`.

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | If using Claude | Anthropic API key |
| `GEMINI_API_KEY` | If using Gemini | Google AI API key |
| `YDOTOOL_SOCKET` | Optional | Path to ydotoold socket (default: `/run/user/1000/.ydotool_socket`) |

---

## Audit Log

All tool calls are logged to:

```
~/.config/hypr-agent/audit.log
```

Each line is a JSON object:

```json
{"timestamp": "2026-04-03T04:00:01Z", "tool": "terminal_run", "args": {"command": "ls ~"}, "result": "Desktop\nDocuments\n..."}
```

The log is **append-only** with no rotation (post-v1.0 feature). Monitor disk usage if running the agent heavily.

---

## Complete Example

```yaml
backend:
  active: claude
  claude:
    model: claude-sonnet-4-6
    api_key_env: ANTHROPIC_API_KEY
  gemini:
    model: gemini-2.5-flash
    api_key_env: GEMINI_API_KEY
  ollama:
    endpoint: http://localhost:11434
    model: llava

loop:
  max_steps: 20
  screenshot_on_every_step: true
  confirm_destructive_actions: true
  kill_switch_key: "ctrl+shift+escape"

safety:
  command_blocklist:
    - "rm -rf /"
    - "dd if="
    - "mkfs"
    - ":(){:|:&};:"
  screenshot_format: png
  ocr_language: eng
```
