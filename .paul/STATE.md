# Project State

## Project Reference

See: .paul/PROJECT.md (updated 2026-04-04)

**Core value:** Any AI client can control a Hyprland/Wayland desktop natively using MCP tools, without Docker or sandboxing, on CachyOS.
**Current focus:** v1.0 MVP complete — all 6 phases finished

## Current Position

Milestone: v1.0 MVP (v1.0.0) — ✅ COMPLETE
Phase: 6 of 6 (Virtual Input Layer) — Complete
Plan: 06-02 unified
Status: Milestone complete — all phases done
Last activity: 2026-04-04 — Phase 6 complete (evdev input layer, ydotool fully removed)

Progress:
- Milestone: [██████████] 100%
- Phase 6: [██████████] 100%

MCP handlers: 25/25 wired ✓
Agent loop: complete ✓ (18 tools)
Multi-backend: complete ✓ (Claude + Gemini + Ollama)
Safety controls: complete ✓
Integration tests: 31/31 pass ✓
Release: v1.0.0 tagged ✓
Hyprland compositor tools: complete ✓ (M2.5)
Virtual input layer: complete ✓ (evdev UInput, no ydotool)

## Loop Position

Current loop state:
```
PLAN ──▶ APPLY ──▶ UNIFY
  ✓        ✓        ✓     [06-02 complete — milestone v1.0 MVP done]
```

## Accumulated Context

### Decisions

| Decision | Phase | Impact |
|----------|-------|--------|
| Wayland-native, no XWayland | Planning | All tool choices constrained to Wayland stack |
| python-evdev UInput for input injection | Phase 6 | Replaces ydotool — no daemon, background-safe, EV_ABS absolute coords |
| stdio transport for MCP | Planning | Best Claude Code compatibility; HTTP optional |
| Strict M0→M13 build order | Planning | No milestone starts until all deps pass acceptance |
| MCP server stub returns TextContent | Phase 1 | Server stays alive before milestones fill in implementations |
| Added Phase 5: Hyprland Integration | Phase 4 complete | Extends milestone — 5 compositor tools via hyprctl (M2.5) |
| Added Phase 6: Virtual Input Layer | Phase 5 complete | Replaces ydotool with python-evdev UInput — background-safe input |
| Fix agent/__init__.py circular import | Phase 6 | Removed eager AgentLoop re-export; no usages existed; zero impact |

### Deferred Issues

| Issue | Origin | Effort | Revisit |
|-------|--------|--------|---------|
| Wire real config to devices.start(cfg) — screen resolution from config.yaml | 06-01/06-02 | S | v1.1 — config loader wiring |
| xkbcommon dynamic key lookup for non-ASCII | SPEC-002 §6 | M | v1.1 |
| Migrate google-generativeai → google-genai (FutureWarning) | Phase 2 | S | v1.1 |
| hyprland_event_subscribe (socket2 live events) | Phase 5 | M | v1.1 |
| grim portal permission setup | PLAN.md risk register | S | User docs |
| Playwright Wayland rendering | PLAN.md risk register | M | v1.1 if needed |
| ydotool doc cleanup (README, docs/, CHANGELOG) | Phase 6 boundary | S | v1.1 docs pass |

### Blockers/Concerns
None — v1.0 MVP fully complete.

## Session Continuity

Last session: 2026-04-04
Stopped at: v1.0 MVP milestone complete — all 6 phases unified
Next action: Start v1.1 milestone planning, or address deferred issues above
Resume file: .paul/phases/06-virtual-input-layer/06-02-SUMMARY.md

---
*STATE.md — Updated after every significant action*
