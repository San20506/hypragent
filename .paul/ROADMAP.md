# Roadmap: HyprAgent

## Overview

HyprAgent builds from zero to a fully functional Wayland desktop automation agent. The journey runs through environment setup, tool-by-tool construction of all MCP-exposed capabilities, safety controls, multi-backend support, end-to-end integration, and a documented v1.0 release. Build order is strictly sequential — each milestone depends on the previous.

## Current Milestone

**v1.0 MVP** (v1.0.0)
Status: ✅ Complete (2026-04-03)
Phases: 5 of 5 complete

## Phases

| Phase | Name | Plans | Status | Completed |
|-------|------|-------|--------|-----------|
| 1 | Design | 1 | ✅ Complete | 2026-04-02 |
| 2 | Construct Core | 5 | ✅ Complete | 2026-04-02 |
| 3 | Construct Extended | 3 | ✅ Complete | 2026-04-02 |
| 4 | Test & Release | 2 | ✅ Complete | 2026-04-03 |
| 5 | Hyprland Integration | 1 | ✅ Complete | 2026-04-03 |

## Phase Details

### Phase 1: Design

**Goal:** Finalize all design artifacts before writing code — interface contracts, MCP schemas, state machine, config schema, project scaffold.
**Depends on:** Nothing (planning complete)
**Research:** Unlikely (decisions already locked in PLAN.md)

**Scope:**
- BackendAdapter ABC interface contract
- MCP tool JSON Schema definitions for all 15+ tools
- Agent loop state machine spec
- `config.yaml` schema
- Wayland permission setup sequence
- Project directory scaffold (empty modules)

**Plans:**
- [ ] 01-01: Design artifacts + project scaffold

---

### Phase 2: Construct Core

**Goal:** M0–M4 complete — environment ready, screenshot/input/OCR/backend working independently.
**Depends on:** Phase 1 (scaffold exists)
**Research:** Likely (ydotool socket path, grim portal permissions, tesseract accuracy)

**Scope:**
- M0: CachyOS environment + all system deps installed
- M1: `tools/screenshot.py` — fullscreen + region capture
- M2: `tools/mouse.py` + `tools/keyboard.py` — ydotool input injection
- M3: `tools/ocr.py` — tesseract screen text extraction
- M4: `agent/backends/` — BackendAdapter + Claude adapter

**Plans:**
- [ ] 02-01: M0 — Environment setup
- [ ] 02-02: M1 — Screenshot capture
- [ ] 02-03: M2 — Mouse & keyboard control
- [ ] 02-04: M3 — OCR / screen reading
- [ ] 02-05: M4 — Backend adapter (Claude first)

---

### Phase 3: Construct Extended

**Goal:** M5–M9 complete — MCP server live, agent loop running, browser/files/terminal tools working.
**Depends on:** Phase 2 (M0–M4 passing acceptance)
**Research:** Unlikely (Playwright Wayland already accounted for)

**Scope:**
- M5: `mcp_server.py` — MCP stdio server exposing all tools
- M6: `agent/loop.py` — full perceive→reason→act loop
- M7: `tools/browser.py` — Playwright browser automation
- M8: `tools/files.py` — file management with safety controls
- M9: `tools/terminal.py` — shell command execution

**Plans:**
- [ ] 03-01: M5 — MCP server
- [ ] 03-02: M6 — Agent loop
- [ ] 03-03: M7 + M8 — Browser + file tools
- [ ] 03-04: M9 — Terminal execution

---

### Phase 4: Test & Release

**Goal:** M10–M13 complete — safety controls, multi-backend, all system tests passing, v1.0.0 tagged.
**Depends on:** Phase 3 (M5–M9 passing acceptance)
**Research:** Unlikely (internal patterns)

**Scope:**
- M10: Kill switch, audit log, destructive action confirmation
- M11: Gemini + Ollama backend adapters
- M12: Full end-to-end integration test
- M13: install.sh, README.md, config.yaml.example, v1.0.0 tag

**Plans:**
- [ ] 04-01: M10 + M11 — Safety controls + multi-backend
- [ ] 04-02: M12 + M13 — Integration + release

---

### Phase 5: Hyprland Integration

**Goal:** M2.5 complete — native compositor awareness via hyprctl; 5 new MCP tools giving Claude Code a full mental map of the desktop before acting.
**Depends on:** Phase 2 M2 (input injection working); no new system deps — hyprctl is part of Hyprland
**Research:** None — hyprctl JSON interface confirmed from Hyprland wiki

**Scope:**
- `tools/hyprland.py` — hyprctl-backed compositor query and control tools
- M2.5-a: `hyprland_workspace_list` — all workspaces with id, name, window count, monitor, active flag
- M2.5-b: `hyprland_workspace_switch` — switch workspace or move active window (dispatch workspace / movetoworkspace / movetoworkspacesilent)
- M2.5-c: `hyprland_clients` — all open windows with class, title, pid, workspace, position, size, floating, fullscreen
- M2.5-d: `hyprland_active_window` — currently focused window (class, title, workspace) — pre-action sanity check
- M2.5-e: `hyprland_focus_window` — focus window by class or address without switching workspace (dispatch focuswindow)
- Deferred to v1.1: `hyprland_event_subscribe` — socket2 live event stream (async, socat-based)
- Wire all 5 tools in `mcp_server.py` (brings tool count to 25)
- Add schemas to `AGENT_TOOLS` in `agent/loop.py`

**Interface:**
- All queries: `hyprctl -j <command>` → parse JSON → return structured dict
- All dispatches: `hyprctl dispatch <action> <args>` → check returncode
- Env: `HYPRLAND_INSTANCE_SIGNATURE` (set automatically by Hyprland, no daemon required)

**Plans:**
- [x] 05-01: M2.5 — Hyprland compositor tools

---
*Roadmap created: 2026-04-02*
*Last updated: 2026-04-03 — Phase 5 complete, v1.0 MVP milestone complete*
