# Changelog

All notable changes to HyprAgent are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versioning follows [Semantic Versioning](https://semver.org/).

---

## [1.0.0] — 2026-04-03

### Added

**Core tools (M1–M9)**
- `take_screenshot` — fullscreen and region capture via `grim`
- `mouse_move`, `mouse_click`, `mouse_drag`, `mouse_scroll` — Wayland-native input via `ydotool`
- `keyboard_type`, `keyboard_press` — text injection and key press via `ydotool`
- `read_screen_text` — OCR text extraction via Tesseract + Pillow
- `browser_open`, `browser_navigate`, `browser_click`, `browser_type`, `browser_scroll`, `browser_get_text` — Playwright browser automation in Wayland mode
- `file_list`, `file_read`, `file_write`, `file_move`, `file_delete` — file management
- `terminal_run` — shell command execution with blocklist, timeout, structured output

**MCP server (M5)**
- `mcp_server.py` — stdio MCP server exposing all 20 tools
- Compatible with Claude Code, OpenCode, any MCP client

**Agent loop (M6)**
- `agent/loop.py` — autonomous perceive → reason → act loop
- Configurable max steps, per-step screenshot, tool dispatch

**Safety controls (M10)**
- SIGINT kill switch (`_killed` flag + signal handler)
- JSON audit log at `~/.config/hypr-agent/audit.log`
- Destructive action confirmation gate (`confirm_destructive_actions` config)
- Terminal command blocklist (`rm -rf /`, `dd if=`, `mkfs`, fork bomb)

**Multi-backend (M11)**
- `ClaudeBackend` — Anthropic API with vision and tool use
- `GeminiBackend` — Google Generative AI with function calling
- `OllamaBackend` — local Ollama models with vision heuristic
- `load_backend(config)` factory for config-driven backend selection

**Testing (M12)**
- 29 integration tests covering all major components
- 26 non-wayland tests pass in CI; 3 wayland tests require live session
- `@pytest.mark.wayland` for hardware-dependent tests

**Release (M13)**
- `install-deps.sh` — automated system dependency installer
- `config.yaml.example` — fully documented configuration template
- `README.md` — setup, MCP integration, usage examples

### Technical Notes

- ydotool scroll implemented via direct `SOCK_DGRAM` socket injection (EV_REL/REL_WHEEL) — ydotool 1.0.4 has no scroll subcommand
- `google-generativeai` 0.8.6 shows FutureWarning (deprecated SDK) — migration to `google-genai` deferred to v1.1

---

## [Unreleased]

### Planned (v1.1)
- Migrate `google-generativeai` → `google-genai` SDK
- Audit log rotation and size limits
- Multi-monitor support
- Voice command input
- Task queue / batch mode

---

*HyprAgent v1.0.0 — initial release, 2026-04-03*
