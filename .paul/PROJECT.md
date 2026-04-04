# HyprAgent

## What This Is

HyprAgent is a native, model-agnostic computer use agent built for Hyprland on Wayland. It replicates and extends the Claude Computer Use capability for CachyOS/Arch Linux environments. The agent exposes all computer interaction capabilities as MCP (Model Context Protocol) tools, allowing any compatible AI client — Claude Code, OpenCode, or custom — to drive full desktop automation.

## Core Value

Any AI client can control a Hyprland/Wayland desktop natively using MCP tools, without Docker or sandboxing, on CachyOS.

## Current State

| Attribute | Value |
|-----------|-------|
| Type | Application |
| Version | 1.0.0 |
| Status | Released — v1.0.0 + Phase 6 (evdev input layer, 25 tools) |
| Last Updated | 2026-04-04 |

## Requirements

### Core Features

- Screenshot capture (full screen + region) via `grim`
- Mouse & keyboard injection via `python-evdev` UInput (Wayland-native, background-safe)
- OCR / screen text extraction via Tesseract
- Browser automation via Playwright (Wayland mode)
- File management tools (list, read, write, move, delete)
- Terminal command execution with structured output
- MCP server exposing all tools over stdio/HTTP
- Agent perceive→reason→act loop with configurable max steps and kill switch
- Safety controls: kill switch, audit log, destructive action confirmation
- Multi-backend support: Claude, Gemini, Ollama (config-driven swap)

### Validated (Shipped)

- ✓ BackendAdapter ABC interface contract — Phase 1
- ✓ All MCP tool schemas defined (20 tools) — Phase 1
- ✓ Agent loop state machine documented — Phase 1
- ✓ Config schema (config.yaml.example) — Phase 1
- ✓ Project scaffold: all module stubs with milestone tags — Phase 1
- ✓ Screenshot capture (fullscreen + region) via grim — Phase 2 M1
- ✓ Mouse & keyboard injection via ydotool — Phase 2 M2
- ✓ OCR screen text extraction via tesseract — Phase 2 M3
- ✓ Claude backend adapter (vision + tool use) — Phase 2 M4
- ✓ MCP server: 20/20 tools wired — Phase 3 M5
- ✓ Perceive→reason→act agent loop — Phase 3 M6
- ✓ Playwright browser automation (Wayland) — Phase 3 M7
- ✓ File management tools with safety controls — Phase 3 M8
- ✓ Terminal execution with blocklist + timeout — Phase 3 M9
- ✓ Kill switch (SIGINT), audit log, destructive action confirmation — Phase 4 M10
- ✓ Gemini + Ollama backend adapters + load_backend factory — Phase 4 M11
- ✓ Integration test suite (29 tests, 26 non-wayland pass) — Phase 4 M12
- ✓ v1.0.0: install.sh, README, config.yaml.example, git tag — Phase 4 M13
- ✓ Hyprland compositor awareness: workspace_list, workspace_switch, clients, active_window, focus_window — Phase 5 M2.5
- ✓ Virtual Input Layer: python-evdev UInput replaces ydotool — background-safe mouse + keyboard, 97-char KEYMAP — Phase 6

### Active (In Progress)
None — v1.0.0 complete.

### Planned (Post-v1.0)
- Migrate `google-generativeai` → `google-genai` SDK (FutureWarning fix)
- Audit log rotation / size limit
- `hyprland_event_subscribe` — socket2 live event stream (async, socat-based) — Phase 5 deferred
- Multi-monitor support
- Voice command input
- Task queue / batch mode
- Web UI dashboard

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
- `python-evdev` requires `uinput` kernel module and user in `input` group (`/dev/uinput` access)
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
| `python-evdev` UInput for input injection | Background-safe; no daemon; replaces ydotool + ydotoold | 2026-04-04 | Active |
| `grim` for screenshots | Wayland-native, compositing-aware | 2026-04-02 | Active |
| `tesseract` for OCR | Battle-tested; supplemented by AI vision when accuracy low | 2026-04-02 | Active |
| `playwright` for browser | Full browser automation with Wayland support | 2026-04-02 | Active |
| stdio transport for MCP | Best Claude Code compatibility | 2026-04-02 | Active |
| ydotool scroll via SOCK_DGRAM socket | ydotool 1.0.4 has no scroll subcommand; direct EV_REL injection works | 2026-04-02 | Superseded — Phase 6 uses evdev REL_WHEEL directly |
| google-generativeai 0.8.6 (deprecated SDK) | google-genai not installed in venv; FutureWarning noted, migration deferred | 2026-04-03 | Deferred |
| Wayland tests marked @pytest.mark.wayland | Hardware-dependent tests skippable in CI | 2026-04-03 | Active |

## Success Metrics

| Metric | Target | Current | Status |
|--------|--------|---------|--------|
| Integration tests passing | 31/31 non-wayland | 31/31 | ✅ |
| No sudo at runtime | 0 sudo calls | 0 | ✅ |
| Backend swap works | claude/gemini/ollama | All 3 load | ✅ |
| Install script success | Clean CachyOS install | install-deps.sh present | ✅ |
| Agent loop task | perceive→reason→act | Implemented + tested | ✅ |
| Compositor awareness | workspace/window query | 5 hyprland tools (25 MCP total) | ✅ |

## Tech Stack / Tools

| Layer | Technology | Notes |
|-------|------------|-------|
| Runtime | Python 3.11+ | via `uv` package manager |
| Screenshot | grim + slurp | Wayland-native |
| Input injection | python-evdev (UInput) | uinput kernel module + /dev/uinput access required |
| Clipboard | wl-clipboard | Wayland-native |
| OCR | tesseract + pytesseract | eng data required |
| Browser | Playwright (Chromium) | --ozone-platform=wayland |
| MCP SDK | `mcp` (Anthropic) | stdio transport |
| AI backends | anthropic, google-generativeai, ollama | Config-driven |
| Config | pyyaml + pydantic | config.yaml |
| Testing | pytest + pytest-asyncio | Integration + unit tests |
| CLI output | rich | Terminal formatting |

---
*PROJECT.md — Evolved through all 6 phases*
*Last updated: 2026-04-04 after Phase 6 (Virtual Input Layer) completion — milestone v1.0 MVP complete*
