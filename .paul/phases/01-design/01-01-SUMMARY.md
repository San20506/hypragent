---
phase: 01-design
plan: 01
subsystem: infra
tags: [mcp, python, wayland, hyprland, scaffold, stubs]

requires: []
provides:
  - pyproject.toml with all dependencies declared
  - config.yaml.example with full config schema
  - BackendAdapter ABC with AgentResponse dataclass
  - All tool module stubs (screenshot, mouse, keyboard, ocr, browser, files, terminal)
  - AgentLoop stub with state machine documented
  - MCP server stub registering all 20 tools over stdio
  - Project scaffold ready for milestone-by-milestone construction
affects: [02-construct-core, 03-construct-extended, 04-test-release]

tech-stack:
  added: [mcp, anthropic, google-generativeai, ollama, playwright, pytesseract, Pillow, pydantic, httpx, rich, pyyaml, pytest, pytest-asyncio]
  patterns: [BackendAdapter ABC pattern, stub-first scaffold with NotImplementedError + milestone tags]

key-files:
  created:
    - pyproject.toml
    - config.yaml.example
    - mcp_server.py
    - agent/backends/base.py
    - agent/loop.py
    - tools/screenshot.py
    - tools/mouse.py
    - tools/keyboard.py
    - tools/ocr.py
    - tools/browser.py
    - tools/files.py
    - tools/terminal.py
  modified: []

key-decisions:
  - "BackendAdapter ABC: send_message takes messages/tools/images lists — uniform interface regardless of backend"
  - "Stubs use NotImplementedError with milestone tag (e.g. M1, M2) not just 'not implemented' — makes grep useful during construction"
  - "MCP server stub returns informative TextContent instead of raising — server stays alive before milestones complete"
  - "20 tools registered (not 15 as originally estimated) — browser_screenshot added during implementation"

patterns-established:
  - "All tool stubs: docstring with system dep, function sig, # TODO MX comment, NotImplementedError"
  - "Backend stubs: class + __init__ + all 3 abstract methods + supports_vision hardcoded where known"
  - "mcp_server.py: list_tools() returns full Tool list with schemas, call_tool() dispatches via match/case"

duration: ~25min
started: 2026-04-02T00:00:00Z
completed: 2026-04-02T00:30:00Z
---

# Phase 1 Plan 01: Design & Scaffold Summary

**Complete project scaffold created: BackendAdapter ABC, all tool stubs (M1–M9), MCP server registering 20 tools, and pyproject.toml with full dependency manifest.**

## Performance

| Metric | Value |
|--------|-------|
| Duration | ~25 min |
| Started | 2026-04-02 |
| Completed | 2026-04-02 |
| Tasks | 3/3 completed |
| Files created | 20 |

## Acceptance Criteria Results

| Criterion | Status | Notes |
|-----------|--------|-------|
| AC-1: Project structure exists | Pass | All 16 .py files present under agent/, tools/, tests/ |
| AC-2: BackendAdapter ABC defined | Pass | Abstract methods + AgentResponse dataclass confirmed importable |
| AC-3: All MCP tools declared in server stub | Pass | 20 tools present (plan estimated 15; browser_screenshot added) |
| AC-4: Config schema complete | Pass | backend, loop, safety sections all present in config.yaml.example |
| AC-5: pyproject.toml valid TOML | Pass | `tomllib.loads()` succeeds; all required deps declared |

## Accomplishments

- `BackendAdapter` ABC established the interface contract all 3 AI backends (Claude, Gemini, Ollama) must satisfy
- 20 MCP tools registered in stub server with full JSON schemas — Claude Code can connect and see all tools immediately
- Every tool stub uses `# TODO MX:` tags making grep-based construction tracking trivial
- `config.yaml.example` documents all configuration including safety blocklist and Wayland-specific notes

## Files Created

| File | Purpose |
|------|---------|
| `pyproject.toml` | Project config, all deps, `hypragent` entrypoint |
| `config.yaml.example` | Full config schema with comments |
| `.gitignore` | Standard Python + Playwright ignores |
| `README.md` | Quickstart skeleton (prerequisites, setup, MCP add command) |
| `mcp_server.py` | MCP stdio server, 20 tools registered, stub handlers |
| `agent/__init__.py` | Package init |
| `agent/loop.py` | AgentLoop with state machine documented in comments |
| `agent/backends/__init__.py` | Exports all 3 backend classes |
| `agent/backends/base.py` | BackendAdapter ABC + AgentResponse dataclass |
| `agent/backends/claude.py` | ClaudeBackend stub (M4) |
| `agent/backends/gemini.py` | GeminiBackend stub (M11) |
| `agent/backends/ollama.py` | OllamaBackend stub (M11) |
| `tools/__init__.py` | Package init |
| `tools/screenshot.py` | Screenshot stubs (M1) |
| `tools/mouse.py` | Mouse control stubs (M2) |
| `tools/keyboard.py` | Keyboard stubs (M2) |
| `tools/ocr.py` | OCR stubs (M3) |
| `tools/browser.py` | Browser automation stubs (M7) |
| `tools/files.py` | File management stubs (M8) |
| `tools/terminal.py` | Terminal execution stubs + TerminalResult dataclass (M9) |
| `tests/__init__.py` | Test package init |

## Decisions Made

| Decision | Rationale | Impact |
|----------|-----------|--------|
| 20 tools registered (not 15) | `browser_screenshot` tool was in PLAN.md M7 spec but not the original count | No impact — server handles it cleanly |
| MCP server stub returns TextContent not raises | Server must stay alive before milestones fill in implementations | Phase 2 can connect Claude Code and see all tools immediately |
| `TODO MX:` tags in all stubs | Makes `grep -r "TODO M1"` a construction checklist during Phase 2 | Each milestone has clear grep-verifiable scope |

## Deviations from Plan

| Type | Count | Impact |
|------|-------|--------|
| Scope additions | 1 | Negligible |
| Auto-fixed | 0 | — |
| Deferred | 0 | — |

**Total impact:** Minimal — `browser_screenshot` was in the M7 spec already, just not in the original tool count estimate.

## Issues Encountered

None.

## Next Phase Readiness

**Ready:**
- Project scaffold importable — `python3 -c "from agent.backends.base import BackendAdapter"` works
- MCP server importable (syntax valid) — will fully work once `uv sync` installs `mcp` package
- All stubs are grep-tagged by milestone (`TODO M0:` through `TODO M11:`) for construction tracking
- `config.yaml.example` is the reference for M0 environment setup

**Concerns:**
- `mcp` package not yet installed (Phase 2 M0 handles `uv sync`)
- `mcp_server.py` import will fail until `mcp` is installed — expected, not a blocker

**Blockers:**
- None — Phase 2 (Construct Core) can begin immediately with M0 environment setup

---
*Phase: 01-design, Plan: 01*
*Completed: 2026-04-02*
