# HyprAgent

## What This Is

HyprAgent is a native, model-agnostic computer use agent built for Hyprland on Wayland. It replicates and extends the Claude Computer Use capability for CachyOS/Arch Linux environments. The agent exposes all computer interaction capabilities as MCP (Model Context Protocol) tools, allowing any compatible AI client — Claude Code, OpenCode, or custom — to drive full desktop automation.

## Core Value

Any AI client can control a Hyprland/Wayland desktop natively using MCP tools, without Docker or sandboxing, on CachyOS.

## Current State

| Attribute | Value |
|-----------|-------|
| Type | Application |
| Version | 0.0.0 |
| Status | Design Complete → Construct Core |
| Last Updated | 2026-04-02 |

## Requirements

### Core Features

- Screenshot capture (full screen + region) via `grim`
- Mouse & keyboard injection via `ydotool` (Wayland-native, uinput)
- OCR / screen text extraction via Tesseract
- Browser automation via Playwright (Wayland mode)
- File management tools (list, read, write, move, delete)
- Terminal command execution with structured output
- MCP server exposing all tools over stdio/HTTP
- Agent perceive→reason→act loop with configurable max steps and kill switch
- Safety controls: kill switch, audit log, destructive action confirmation
- Multi-backend support: Claude, Gemini, Ollama (config-driven swap)

### Validated (Shipped)
- [x] BackendAdapter ABC interface contract — Phase 1
- [x] All MCP tool schemas defined (20 tools) — Phase 1
- [x] Agent loop state machine documented — Phase 1
- [x] Config schema (config.yaml.example) — Phase 1
- [x] Project scaffold: all module stubs with milestone tags — Phase 1

### Active (In Progress)
None yet.

### Planned (Next)
- Phase 2: Construct Core (M0–M4: ENV → SCREEN → INPUT → OCR → BACKEND)
- Phase 3: Construct Extended (M5–M9: MCP → LOOP → BROWSER → FILES → TERMINAL)
- Phase 4: Test & Release (M10–M13: SAFETY → MULTI-BACKEND → INTEGRATION → RELEASE)

### Out of Scope
- Multi-monitor support — deferred to v1.1+
- Voice command input — deferred to v1.1+
- Task queue / batch mode — deferred to v1.1+
- Web UI dashboard — deferred to v1.1+
- XWayland compatibility — Wayland-native only

## Target Users

**Primary:** Power users and developers on CachyOS/Arch Linux + Hyprland who want AI-driven desktop automation.
- Comfortable with terminal, systemd, and Wayland tooling
- Want model-agnostic control (not locked to Claude)

## Constraints

### Technical Constraints
- Wayland-native only — no XWayland fallback
- `ydotool` requires `uinput` kernel module and `ydotoold` daemon running
- `grim` requires `xdg-desktop-portal-hyprland` for screenshot permissions
- Playwright must run with `--ozone-platform=wayland`
- Python 3.11+ runtime
- MCP transport: stdio (default), HTTP optional via `--http` flag
- No Docker, no sandbox — runs on live desktop

### Business Constraints
- No sudo required for any operation at runtime
- All credentials via environment variables — no hardcoded keys
- Build order strictly sequential: M0 → M13 (each milestone depends on prior)

## Key Decisions

| Decision | Rationale | Date | Status |
|----------|-----------|------|--------|
| Wayland-native stack (no XWayland) | Target platform is Hyprland; XWayland adds complexity | 2026-04-02 | Active |
| MCP as orchestration protocol | Model-agnostic; works with Claude Code, OpenCode, custom clients | 2026-04-02 | Active |
| `ydotool` for input injection | Only Wayland-native input injector; requires uinput | 2026-04-02 | Active |
| `grim` for screenshots | Wayland-native, compositing-aware | 2026-04-02 | Active |
| `tesseract` for OCR | Battle-tested; supplemented by AI vision when accuracy low | 2026-04-02 | Active |
| `playwright` for browser | Full browser automation with Wayland support | 2026-04-02 | Active |
| stdio transport for MCP | Best Claude Code compatibility | 2026-04-02 | Active |
| MCP server stub returns TextContent not raises | Server stays alive before milestones fill in — Phase 1 | 2026-04-02 | Active |
| TODO MX: tags in all stubs | Grep-verifiable construction checklist during Phase 2 | 2026-04-02 | Active |

## Success Metrics

| Metric | Target | Current | Status |
|--------|--------|---------|--------|
| System tests passing | 10/10 | 0/10 | Not started |
| No sudo at runtime | 0 sudo calls | - | Not started |
| Backend swap works | claude/gemini/ollama | - | Not started |
| Install script success | Clean CachyOS install | - | Not started |
| Agent loop task | 3-step task autonomous | - | Not started |

## Tech Stack / Tools

| Layer | Technology | Notes |
|-------|------------|-------|
| Runtime | Python 3.11+ | via `uv` package manager |
| Screenshot | grim + slurp | Wayland-native |
| Input injection | ydotool + ydotoold | uinput kernel module required |
| Clipboard | wl-clipboard | Wayland-native |
| OCR | tesseract + pytesseract | eng data required |
| Browser | Playwright (Chromium) | --ozone-platform=wayland |
| MCP SDK | `mcp` (Anthropic) | stdio transport |
| AI backends | anthropic, google-generativeai, ollama | Config-driven |
| Config | pyyaml + pydantic | config.yaml |
| Testing | pytest | System + unit tests |
| CLI output | rich | Terminal formatting |

---
*PROJECT.md — Updated after Phase 1 (Design) completion*
*Last updated: 2026-04-02*
