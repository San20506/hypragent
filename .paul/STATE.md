# Project State

## Project Reference

See: .paul/PROJECT.md (updated 2026-04-02)

**Core value:** Any AI client can control a Hyprland/Wayland desktop natively using MCP tools, without Docker or sandboxing, on CachyOS.
**Current focus:** Phase 2 — Construct Core (M0–M4)

## Current Position

Milestone: v1.0 MVP (v1.0.0)
Phase: 2 of 4 (Construct Core) — In Progress
Plan: 04-02 created, awaiting approval
Status: PLAN created, ready for APPLY
Last activity: 2026-04-03 — Created 04-02 M12+M13 Integration+Release plan

Progress:
- Milestone: [█████████░] 97%
- Phase 4: [█████░░░░░] 50%

MCP handlers: 20/20 wired ✓
Agent loop: complete ✓
Multi-backend: complete ✓ (Claude + Gemini + Ollama)
Safety controls: complete ✓

## Loop Position

Current loop state:
```
PLAN ──▶ APPLY ──▶ UNIFY
  ✓        ○        ○     [Plan created, awaiting approval]
```

## Accumulated Context

### Decisions

| Decision | Phase | Impact |
|----------|-------|--------|
| Wayland-native, no XWayland | Planning | All tool choices constrained to Wayland stack |
| ydotool for input injection | Planning | uinput kernel module + ydotoold daemon required at M0 |
| stdio transport for MCP | Planning | Best Claude Code compatibility; HTTP optional |
| Strict M0→M13 build order | Planning | No milestone starts until all deps pass acceptance |
| MCP server stub returns TextContent | Phase 1 | Server stays alive before milestones fill in implementations |
| TODO MX: tags in all stubs | Phase 1 | Grep-verifiable milestone scope during construction |

### Deferred Issues

| Issue | Origin | Effort | Revisit |
|-------|--------|--------|---------|
| YDOTOOL_SOCKET=/run/user/1000/.ydotool_socket must be set in all ydotool subprocess calls | M0 verified | S | M2 — tools/mouse.py + tools/keyboard.py |
| ydotool.service shows start-limit-hit (cosmetic, daemon runs fine); fix unit type | M0 verified | S | Pre-release (M13) |
| grim portal permission setup | PLAN.md risk register | S | M0 setup |
| Playwright Wayland rendering | PLAN.md risk register | M | M7 implementation |

### Blockers/Concerns
None yet.

## Session Continuity

Last session: 2026-04-02
Stopped at: Plan 04-01 unified (M10+M11 complete)
Next action: /paul:plan for Phase 4 Plan 02 — M12 integration test + M13 release
Resume file: .paul/phases/04-test-release/04-01-SUMMARY.md

---
*STATE.md — Updated after every significant action*
