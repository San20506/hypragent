---
phase: 06-virtual-input-layer
plan: 01
subsystem: input
tags: [evdev, uinput, virtual-devices, device-manager, wayland]

requires:
  - phase: 02-construct-core
    provides: mouse.py and keyboard.py patterns being replaced

provides:
  - DeviceManager singleton with start()/stop()/verify() lifecycle
  - UInput virtual keyboard "HyprAgent Keyboard" at startup
  - UInput virtual mouse "HyprAgent Mouse" (EV_ABS + INPUT_PROP_DIRECT) at startup
  - mcp_server.py lifespan hook for device creation/teardown
  - config.yaml.example tools.mouse + tools.keyboard config section
  - evdev>=1.6 declared in pyproject.toml

affects: 06-02-virtual-input-layer (tool rewrites depend on devices singleton)

tech-stack:
  added: [evdev==1.9.3]
  patterns: [module-level singleton for shared hardware resource, defer UInput creation to start()]

key-files:
  created: [agent/device_manager.py]
  modified: [mcp_server.py, config.yaml.example, pyproject.toml, uv.lock]

key-decisions:
  - "Config stub: devices.start() called with no config — uses defaults (2560×1440); TODO(06-02) to wire real config"
  - "INPUT_PROP_DIRECT: required for Hyprland to accept EV_ABS absolute coordinates"
  - "Deferred UInput creation: devices = DeviceManager() at import time, UInput created only on start()"

patterns-established:
  - "DeviceManager singleton: import devices from agent.device_manager in tool modules"
  - "Lifespan pattern: devices.start() before stdio_server, devices.stop() in finally"

duration: 15min
started: 2026-04-04T00:00:00Z
completed: 2026-04-04T00:15:00Z
---

# Phase 6 Plan 01: Virtual Input Layer — Device Manager Summary

**DeviceManager singleton created with UInput virtual keyboard + absolute mouse; evdev==1.9.3 installed; mcp_server lifespan hook wired.**

## Performance

| Metric | Value |
|--------|-------|
| Duration | ~15 min |
| Tasks | 4 completed |
| Files modified | 4 (1 created, 3 modified) |

## Acceptance Criteria Results

| Criterion | Status | Notes |
|-----------|--------|-------|
| AC-1: DeviceManager creates both virtual devices | Pass | start() creates HyprAgent Keyboard + Mouse via UInput |
| AC-2: Correct public interface | Pass | keyboard, mouse, start(), stop(), verify() all present |
| AC-3: MCP server lifespan hook | Pass | devices.start/stop in _run() try/finally |
| AC-4: Config schema includes resolution fields | Pass | tools.mouse.screen_width/height + keyboard section added |
| AC-5: evdev dependency declared | Pass | evdev>=1.6 in pyproject.toml; evdev==1.9.3 installed |

## Files Created/Modified

| File | Change | Purpose |
|------|--------|---------|
| `agent/device_manager.py` | Created | DeviceManager class + `devices` singleton |
| `mcp_server.py` | Modified | Added `from agent.device_manager import devices`; lifespan hook in `_run()` |
| `config.yaml.example` | Modified | Added `tools:` section with mouse resolution + keyboard config |
| `pyproject.toml` | Modified | Added `evdev>=1.6` dependency |
| `uv.lock` | Modified | evdev==1.9.3 resolved and locked |

## Decisions Made

| Decision | Rationale | Impact |
|----------|-----------|--------|
| Config not wired to DeviceManager.start() | No config loader in mcp_server.py scope yet; plan boundary prevents touching tool handlers | TODO(06-02) to pass real config; defaults to 2560×1440 |
| EV_ABS + INPUT_PROP_DIRECT for mouse | SPEC-002 §4.2: without INPUT_PROP_DIRECT, Hyprland ignores absolute coordinate events | Critical for VD-03 acceptance criterion |
| Deferred UInput instantiation | Creating UInput at module import time would require /dev/uinput access even when not running as MCP server | More robust; devices.start() called explicitly |

## Deviations from Plan

### Summary

| Type | Count | Impact |
|------|-------|--------|
| Config stub | 1 | devices.start() uses 2560×1440 defaults; TODO left for 06-02 |

### Auto-fixed Issues

None — plan executed as written.

### Deferred Items

- TODO(06-02): pass real config object to `devices.start(cfg)` once config loader is wired in mcp_server.py

## Issues Encountered

| Issue | Resolution |
|-------|------------|
| evdev not installed when Task 1 qualified | Task 4 (install evdev) executed before Task 1 re-qualification; all subsequent verifications passed |

## Next Phase Readiness

**Ready:**
- `devices` singleton importable: `from agent.device_manager import devices`
- `devices.keyboard` and `devices.mouse` are live UInput instances after `devices.start()`
- mcp_server.py will call `devices.start()` at server startup — tools can use devices immediately
- Config schema ready for tool modules to read `screen_width/height` and `type_delay_ms`

**Concerns:**
- `devices.start()` called without config — resolution defaults to 2560×1440. If user's display differs, mouse positioning will be wrong until 06-02 wires real config.
- FutureWarning from google-generativeai is pre-existing, unrelated to this plan.

**Blockers:**
- None — 06-02 can proceed immediately.

---
*Phase: 06-virtual-input-layer, Plan: 01*
*Completed: 2026-04-04*
