---
phase: 02-construct-core
plan: 03
status: complete
commit: 6e84774
date: 2026-04-02
---

# Summary: Plan 02-03 — M2 Mouse & Keyboard

## What Was Built

All 3 tasks complete. M2 input control fully implemented and wired.

### tools/mouse.py
- `move_mouse(x, y)` — `ydotool mousemove --absolute -x Y -y Y`
- `click(x, y, button)` — move then `ydotool click 0xC0/C1/C2`
- `double_click(x, y)` — two left clicks with 50ms delay
- `drag(from_x, from_y, to_x, to_y)` — 0x40 (down) + move + 0x80 (up)
- `scroll(x, y, direction, amount)` — move then REL_WHEEL via ydotoold socket (SOCK_DGRAM)
- Shared `_ydotool(*args)` helper: subprocess with `{**os.environ, "YDOTOOL_SOCKET": ...}` env

### tools/keyboard.py
- `type_text(text)` — `ydotool type --delay 20 -- {text}`
- `press_key(key)` — `ydotool key {key}` (X11 keysym, supports "ctrl+c" syntax)
- `hotkey(*keys)` — delegates to `press_key("+".join(keys))`
- Same `_ydotool` helper pattern, YDOTOOL_SOCKET via env dict

### mcp_server.py
- Added imports: `from tools.mouse import ...`, `from tools.keyboard import ...`
- Replaced 6 `_stub("M2", name)` cases with real implementations
- Each handler: try/except with `TextContent("OK")` or `TextContent("Error: {e}")`

## Deviations from Plan

### scroll() implementation changed
**Plan specified:** `ydotool scroll --axis-x 0 --axis-y N`
**Actual:** `ydotool 1.0.4` has no `scroll` subcommand (only: click, mousemove, type, key)
**Fix:** Inject `REL_WHEEL` events directly via the ydotoold Unix datagram socket using
`socket.SOCK_DGRAM` + `struct.pack("qqHHi", sec, usec, EV_REL, REL_WHEEL, value)`.
This was discovered during verification, fixed, and re-verified successfully.

## Verification Results
```
move_mouse: OK
click left: OK
click right: OK
scroll down: OK
scroll up: OK
press_key Return: OK
hotkey ctrl+shift: OK
mcp_server.py wired: OK
```

## Known Issues / Deferred
- YDOTOOL_SOCKET hardcoded to `/run/user/1000/.ydotool_socket` (config-driven in M13)
- `type_text` performance: 20ms/char delay means ~50 chars/sec; acceptable for MVP
- `drag()` not tested live (requires visible target) — structural implementation only
