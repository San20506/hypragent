## Why

The HYPR Agent desktop version (CachyOS/Hyprland) is complete with MCP server, agent loop, and all tools. Phase 3 ports the architecture to Android, replacing Wayland-native tools (grim, ydotool) with Android equivalents (Accessibility Service, dispatchGesture) and adding Android-specific concerns: foreground service for process survival, consent management for per-app permissions, and emergency stop independent of the WebSocket bridge.

The original Phase 3 design document (`HYPR_Agent_Android_Phase3_Design.md`) defines the architecture and build order. This change decomposes that design into 8 implementable specs, resolves 15 architectural issues identified during critic review, and produces the task breakdown for Phase 4 (Construct).

## What Changes

Eight new capabilities are introduced for the Android port:

1. **Accessibility Service** — UI tree reading, gesture dispatch, OCR fallback trigger (Layer A I/O module)
2. **Foreground Service** — Termux core embedding, persistent notification, Phantom Process Killer resilience
3. **WebSocket Bridge** — Local IPC between Layer A and Layer B with command/result/event protocol, reconnect, idempotency
4. **Consent Manager** — Per-app + per-permission session grants, prompt UI, revoke affordance, concurrent prompt queueing
5. **Emergency Stop** — Always-reachable kill control independent of WebSocket, post-stop command rejection
6. **MCP Tool Schema & Hermes Agent** — Android-native tool definitions, reasoning loop, AI backend adapter, termux_exec
7. **Task Status UI** — Plain language status display in notification and optional overlay
8. **Audit Logger** — Append-only JSON log with async writes, cross-layer event logging

No existing capabilities are modified. The desktop version remains unchanged.

## Capabilities

### New Capabilities

- `accessibility-service`: Android Accessibility Service with UI tree reader, gesture dispatcher, OCR fallback trigger, and intent resolver for consent timing
- `foreground-service`: Foreground service with Termux core embedding (child process via Termux:Plugin API), persistent notification with controls, Phantom Process Killer survival
- `websocket-bridge`: Local WebSocket (127.0.0.1) with Layer B as server, Layer A as client; JSON command/result/event messages; idempotent re-issue on reconnect; heartbeat keepalive; message size limits; screen staleness detection
- `consent-manager`: Session-grant model scoped per app + per permission type; in-memory storage; concurrent prompt queueing; integration with emergency stop
- `emergency-stop`: Multi-trigger kill (notification, hardware button, optional shake); post-stop command rejection; WebSocket-independent execution; consent revocation on stop
- `mcp-tool-schema-hermes-agent`: Android-native MCP tools (screen_read, tap, swipe, long_press, pinch, read_screen_text, file_*, termux_exec); Hermes Agent perceive-reason-act loop; Claude/Gemini/Ollama backend adapter; scoped termux_exec (Termux $HOME)
- `task-status-ui`: Plain language status in persistent notification; optional overlay; current step count (no total); action history
- `audit-logger`: Append-only JSON; async non-blocking writes; log rotation (10MB, 5 files); cross-layer event logging from Layer A via WebSocket

### Modified Capabilities

None. This change adds new capabilities only.

## Impact

**Affected code:** New Kotlin modules for Layer A (accessibility service, foreground service, consent manager, emergency stop, task status UI). New Termux-based modules for Layer B (MCP server, Hermes Agent, backend adapter, audit logger). WebSocket bridge code in both layers.

**Affected APIs:** New local WebSocket protocol (command/result/event JSON). New MCP tool schema (Android-native tools). No changes to existing desktop MCP server or tools.

**Affected dependencies:**
- Android SDK (Accessibility Service API, Foreground Service API, WebSocket)
- Termux:Plugin API or bundled bootstrap for core embedding
- Existing Python MCP server (adapted for Termux environment)
- AI backend SDKs (Anthropic, Google, Ollama) — same as desktop

**Systems affected:** This is a new Android app. No existing systems are modified. The desktop HyprAgent remains untouched.

**Risks:**
- Phantom Process Killer survival is the critical path — if the foreground service can't keep Termux alive, nothing else works
- Consent timing requires intent resolver (tap coordinates → app package) which is non-trivial on Android
- WebSocket idempotency adds complexity to the reconnect logic
