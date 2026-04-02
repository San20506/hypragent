# Project State

## Project Reference

See: .paul/PROJECT.md (updated 2026-04-02)

**Core value:** Any AI client can control a Hyprland/Wayland desktop natively using MCP tools, without Docker or sandboxing, on CachyOS.
**Current focus:** Phase 2 — Construct Core (M0–M4)

## Current Position

Milestone: v1.0 MVP (v1.0.0)
Phase: 2 of 4 (Construct Core) — In Progress
Plan: 02-05 created, awaiting approval
Status: PLAN created, ready for APPLY
Last activity: 2026-04-02 — Created 02-05 M4 Claude Backend plan

Progress:
- Milestone: [███████░░░] 65%
- Phase 2: [████████░░] 80%

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
Stopped at: Plan 02-04 unified
Next action: /paul:plan for Phase 2 Plan 05 — M4 Backend Adapter (agent/backends/claude.py)
Resume file: .paul/phases/02-construct-core/02-04-SUMMARY.md

---
*STATE.md — Updated after every significant action*
