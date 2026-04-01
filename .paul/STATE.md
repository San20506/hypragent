# Project State

## Project Reference

See: .paul/PROJECT.md (updated 2026-04-02)

**Core value:** Any AI client can control a Hyprland/Wayland desktop natively using MCP tools, without Docker or sandboxing, on CachyOS.
**Current focus:** Phase 2 — Construct Core (M0–M4)

## Current Position

Milestone: v1.0 MVP (v1.0.0)
Phase: 2 of 4 (Construct Core) — Ready to plan
Plan: Not started
Status: Ready to plan
Last activity: 2026-04-02 — Phase 1 complete, transitioned to Phase 2

Progress:
- Milestone: [██░░░░░░░░] 25%
- Phase 2: [░░░░░░░░░░] 0%

## Loop Position

Current loop state:
```
PLAN ──▶ APPLY ──▶ UNIFY
  ✓        ✓        ✓     [Loop complete — ready for next PLAN]
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
| ydotool socket path config | PLAN.md risk register | S | M2 implementation |
| grim portal permission setup | PLAN.md risk register | S | M0 setup |
| Playwright Wayland rendering | PLAN.md risk register | M | M7 implementation |

### Blockers/Concerns
None yet.

## Session Continuity

Last session: 2026-04-02
Stopped at: Plan 01-01 created
Next action: Run /paul:plan for Phase 2 (Construct Core — M0 environment setup first)
Resume file: .paul/ROADMAP.md

---
*STATE.md — Updated after every significant action*
