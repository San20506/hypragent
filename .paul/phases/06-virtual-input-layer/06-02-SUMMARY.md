---
phase: 06-virtual-input-layer
plan: 02
subsystem: input
tags: [evdev, uinput, keyboard, mouse, keymap, wayland]

requires:
  - phase: 06-virtual-input-layer (06-01)
    provides: DeviceManager singleton with devices.mouse + devices.keyboard live UInput instances

provides:
  - tools/mouse.py rewritten: EV_ABS absolute positioning via DeviceManager, no subprocess
  - tools/keyboard.py rewritten: 97-char static KEYMAP + clipboard fallback, no subprocess
  - ydotool/ydotoold fully removed from codebase and install-deps.sh
  - agent/__init__.py circular import fix (eager AgentLoop re-export removed)

affects: Phase 6 complete — all ydotool dependencies eliminated from runtime path

tech-stack:
  added: []
  patterns: [static keymap dict[str, tuple[int, bool]] for evdev char injection, clipboard fallback for unmapped chars]

key-files:
  created: []
  modified: [tools/mouse.py, tools/keyboard.py, install-deps.sh, pyproject.toml, tests/test_integration.py, agent/__init__.py]

key-decisions:
  - "Fix agent/__init__.py circular import: removed eager AgentLoop re-export; no usages of `from agent import AgentLoop` exist"
  - "97-char KEYMAP covers a-z, A-Z, 0-9, whitespace, all common ASCII symbols with correct shift flags"
  - "Clipboard fallback (_paste_via_clipboard) handles unmapped chars via wl-copy + ctrl+v"

patterns-established:
  - "tools.mouse / tools.keyboard: import devices from agent.device_manager, never subprocess for input injection"
  - "KEYMAP pattern: char -> (keycode, needs_shift) — extend for non-ASCII in v1.1 via xkbcommon"

duration: 20min
started: 2026-04-04T12:30:00Z
completed: 2026-04-04T12:50:00Z
---

# Phase 6 Plan 02: Virtual Input Layer — Tool Rewrites Summary

**tools/mouse.py and tools/keyboard.py rewritten to use evdev UInput exclusively; ydotool/ydotoold fully removed from codebase, install-deps.sh, and markers; 31/31 non-wayland tests pass.**

## Performance

| Metric | Value |
|--------|-------|
| Duration | ~20 min |
| Tasks | 4 completed |
| Files modified | 6 (0 created, 6 modified) |

## Acceptance Criteria Results

| Criterion | Status | Notes |
|-----------|--------|-------|
| AC-1: mouse.py uses UInput EV_ABS | Pass | move_mouse writes ABS_X/ABS_Y + syn(); no subprocess |
| AC-2: click sends button down/up events | Pass | BTN_LEFT/RIGHT/MIDDLE value=1 then value=0, each with syn() |
| AC-3: keyboard.py types ASCII via keymap, fallback for unknowns | Pass | 97-char KEYMAP; _paste_via_clipboard for unmapped chars |
| AC-4: press_key resolves key names to evdev keycodes | Pass | modifier down → key down/up → modifier up sequence |
| AC-5: install-deps.sh has no ydotool references | Pass | grep returns 0; evdev verify hint added |
| AC-6: tools still importable (no regression) | Pass | 31/31 non-wayland tests pass |

## Files Created/Modified

| File | Change | Purpose |
|------|--------|---------|
| `tools/mouse.py` | Rewritten | EV_ABS mouse via DeviceManager; removed _ydotool, subprocess, socket, struct |
| `tools/keyboard.py` | Rewritten | Static KEYMAP + evdev key injection; removed _ydotool, YDOTOOL_SOCKET |
| `install-deps.sh` | Modified | Removed ydotool pacman install, ydotoold systemctl lines; added evdev verify hint |
| `pyproject.toml` | Modified | Wayland marker: "ydotoold" → "/dev/uinput access" |
| `tests/test_integration.py` | Modified | Module docstring: "ydotoold" → "/dev/uinput" |
| `agent/__init__.py` | Modified | Removed eager `from agent.loop import AgentLoop` re-export (circular import fix) |

## Decisions Made

| Decision | Rationale | Impact |
|----------|-----------|--------|
| Fix agent/__init__.py circular import | tools.mouse → agent → agent.loop → tools.mouse chain blocked import | No functional impact; no code uses `from agent import AgentLoop` |
| KEYMAP size 97 chars | Covers full printable ASCII + whitespace + common symbols; exceeds AC requirement of >80 | Handles most real-world typing without clipboard fallback |
| Clipboard fallback via wl-copy + ctrl+v | SPEC-002 §6 specified; handles emoji, accented chars, anything not in KEYMAP | Requires wl-clipboard installed (already in install-deps.sh) |

## Deviations from Plan

### Summary

| Type | Count | Impact |
|------|-------|--------|
| Auto-fixed | 1 | Circular import; zero functional regression |
| Scope additions | 0 | — |
| Deferred | 0 | — |

### Auto-fixed Issues

**1. Circular Import — agent/__init__.py eager re-export**
- **Found during:** Task 1 verify (`from tools.mouse import ...`)
- **Issue:** `tools.mouse → agent → agent.loop → tools.mouse` circular import at module init
- **Fix:** Changed `agent/__init__.py` from `from agent.loop import AgentLoop` + `__all__` to a single comment
- **Files:** `agent/__init__.py`
- **Verification:** Import test passed; all 31 non-wayland tests still pass
- **Impact:** All AgentLoop usages throughout codebase use `from agent.loop import AgentLoop` directly — confirmed by grep

### Deferred Items

- xkbcommon dynamic key lookup (SPEC-002 §6 deferred to v1.1) — static KEYMAP is correct for v1.0

## Issues Encountered

| Issue | Resolution |
|-------|------------|
| Circular import: tools.mouse → agent → agent.loop → tools.mouse | Removed eager re-export from agent/__init__.py; verified no usages of `from agent import AgentLoop` |

## Next Phase Readiness

**Ready:**
- Phase 6 complete: all ydotool dependencies eliminated from runtime code, install script, and markers
- tools/mouse.py and tools/keyboard.py use evdev UInput exclusively — background-safe input injection
- KEYMAP covers 97 chars; clipboard fallback handles edge cases
- MCP server lifespan (from 06-01) starts devices before tools are called
- All 31 non-wayland integration tests pass; no regressions

**Concerns:**
- devices.start() still uses 2560×1440 defaults (config not wired end-to-end) — TODO in mcp_server.py
- wayland-marked tests (6) not runnable without a live Hyprland session — expected
- google-generativeai FutureWarning is pre-existing, unrelated to Phase 6

**Blockers:**
- None — Phase 6 complete

---
*Phase: 06-virtual-input-layer, Plan: 02*
*Completed: 2026-04-04*
