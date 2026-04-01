# Roadmap: HyprAgent

## Overview

HyprAgent builds from zero to a fully functional Wayland desktop automation agent. The journey runs through environment setup, tool-by-tool construction of all MCP-exposed capabilities, safety controls, multi-backend support, end-to-end integration, and a documented v1.0 release. Build order is strictly sequential — each milestone depends on the previous.

## Current Milestone

**v1.0 MVP** (v1.0.0)
Status: In progress
Phases: 1 of 4 complete

## Phases

| Phase | Name | Plans | Status | Completed |
|-------|------|-------|--------|-----------|
| 1 | Design | 1 | ✅ Complete | 2026-04-02 |
| 2 | Construct Core | 5 | Not started | - |
| 3 | Construct Extended | 4 | Not started | - |
| 4 | Test & Release | 2 | Not started | - |

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
*Roadmap created: 2026-04-02*
*Last updated: 2026-04-02*
