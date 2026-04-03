# MCP Tool API Reference

HyprAgent exposes 20 MCP tools over stdio. All tools return `TextContent` with a string result.

---

## Screenshot Tools

### `take_screenshot`

Captures the screen or a region.

**Input:**
```json
{
  "region": {
    "x": 0,
    "y": 0,
    "width": 1920,
    "height": 1080
  }
}
```

`region` is optional. Omit for fullscreen.

**Output:** Base64-encoded PNG string.

---

### `read_screen_text`

Extracts text from screen using OCR (Tesseract).

**Input:**
```json
{
  "region": {
    "x": 0,
    "y": 0,
    "width": 800,
    "height": 200
  }
}
```

`region` is optional. Omit for full screen OCR.

**Output:** Extracted text string.

---

## Mouse Tools

### `mouse_move`

Moves the cursor to absolute screen coordinates.

**Input:**
```json
{ "x": 500, "y": 300 }
```

**Output:** `"OK"`

---

### `mouse_click`

Moves to coordinates and clicks.

**Input:**
```json
{ "x": 500, "y": 300, "button": "left" }
```

`button`: `"left"` (default) | `"right"` | `"middle"`

**Output:** `"OK"`

---

### `mouse_drag`

Click-drags from one position to another.

**Input:**
```json
{ "from_x": 100, "from_y": 100, "to_x": 400, "to_y": 400 }
```

**Output:** `"OK"`

---

### `mouse_scroll`

Scrolls at a screen position.

**Input:**
```json
{ "x": 500, "y": 300, "direction": "down", "amount": 3 }
```

`direction`: `"up"` | `"down"`
`amount`: number of scroll ticks (default `3`)

**Output:** `"OK"`

---

## Keyboard Tools

### `keyboard_type`

Types text into the focused window.

**Input:**
```json
{ "text": "hello world" }
```

**Output:** `"OK"`

---

### `keyboard_press`

Presses a key or key combination.

**Input:**
```json
{ "key": "ctrl+c" }
```

Examples: `"Return"`, `"Escape"`, `"ctrl+z"`, `"alt+F4"`, `"super+d"`

**Output:** `"OK"`

---

## Browser Tools

### `browser_open`

Launches Chromium in Wayland mode. Creates a persistent singleton session.

**Input:** `{}`

**Output:** `"OK"`

---

### `browser_navigate`

Navigates to a URL in the open browser.

**Input:**
```json
{ "url": "https://example.com" }
```

**Output:** `"OK"`

---

### `browser_click`

Clicks an element matching a CSS selector.

**Input:**
```json
{ "selector": "#submit-button" }
```

**Output:** `"OK"`

---

### `browser_type`

Types text into an element matching a CSS selector.

**Input:**
```json
{ "selector": "input[name='q']", "text": "search query" }
```

**Output:** `"OK"`

---

### `browser_scroll`

Scrolls the browser page.

**Input:**
```json
{ "direction": "down", "amount": 300 }
```

`direction`: `"up"` | `"down"`
`amount`: pixels to scroll

**Output:** `"OK"`

---

### `browser_get_text`

Returns the visible text content of the current page.

**Input:** `{}`

**Output:** Page text as string.

---

## File Tools

### `file_list`

Lists directory contents.

**Input:**
```json
{ "path": "/home/user/Documents" }
```

**Output:** JSON array:
```json
[
  { "name": "notes.txt", "is_dir": false, "size": 1024 },
  { "name": "projects", "is_dir": true, "size": 0 }
]
```

---

### `file_read`

Reads a file as text.

**Input:**
```json
{ "path": "/home/user/notes.txt" }
```

**Output:** File contents as string.

---

### `file_write`

Writes text to a file (overwrites).

**Input:**
```json
{ "path": "/tmp/output.txt", "content": "hello\nworld" }
```

Requires confirmation if `confirm_destructive_actions: true`.

**Output:** `"OK"`

---

### `file_move`

Moves or renames a file.

**Input:**
```json
{ "src": "/tmp/a.txt", "dst": "/tmp/b.txt" }
```

**Output:** `"OK"`

---

### `file_delete`

Deletes a file.

**Input:**
```json
{ "path": "/tmp/old.txt" }
```

**Output:** `"OK"`

---

## Terminal Tool

### `terminal_run`

Executes a shell command and returns structured output.

**Input:**
```json
{ "command": "ls -la ~", "timeout": 30 }
```

`timeout`: seconds before kill (default `30`)

Commands matching the blocklist (`rm -rf /`, `dd if=`, `mkfs`, fork bomb) are **always rejected**.

**Output:**
```json
{
  "returncode": 0,
  "stdout": "total 48\ndrwxr-xr-x ...",
  "stderr": "",
  "timed_out": false
}
```

On blocklist hit: raises `ValueError: Command blocked: <reason>`

---

## Error Handling

All tools return a string result. On error:
- File tools: return error message string starting with `"Error:"`
- Terminal: `returncode != 0` and `stderr` contains the error
- Mouse/keyboard: raise on `ydotool` failure

Unknown tool name via `_dispatch_tool`: returns `"Unknown tool: <name>"`
