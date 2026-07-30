# HYPR Agent (Android) — Phase 3: Design

Companion doc to the Phase 1 Formation and Phase 2 Requirements already agreed. Covers architectural blueprint, internal/external design surfaces, and the design review checklist to clear before Phase 4 (Construct).

---

## 1. Architecture Blueprint

Three layers, same shape as the original PDF concept, now with module boundaries drawn.

```
┌─────────────────────────────────────────────┐
│ Layer A — Native Android App                │
│  ├─ Hermes GUI (Kotlin)                      │
│  ├─ Accessibility Service                    │
│  │    ├─ UI-tree reader                      │
│  │    ├─ Gesture dispatcher (tap/swipe/etc.) │
│  │    └─ OCR fallback trigger                │
│  ├─ Foreground Service (persistent notif.)   │
│  └─ Consent Manager (session-grant store)    │
└─────────────────────────────────────────────┘
                    │ Local WebSocket (127.0.0.1)
┌─────────────────────────────────────────────┐
│ Layer B — Embedded Termux Core               │
│  ├─ Hermes Agent (reasoning loop)            │
│  ├─ HYPR Agent MCP server                    │
│  │    ├─ Tool schema (Android-native)        │
│  │    ├─ Audit logger (append-only JSON)     │
│  │    └─ termux_exec (scoped shell)          │
│  └─ AI Backend Adapter (Claude/Gemini/Ollama)│
└─────────────────────────────────────────────┘
                    │ HTTPS (only anonymized
                    │  prompt + screen context)
┌─────────────────────────────────────────────┐
│ Layer C — External LLM API                   │
└─────────────────────────────────────────────┘
```

**Module boundaries:**
- Native App never talks to the LLM API directly — everything routes through Layer B. This keeps the consent gate as the single choke point for any data leaving the device.
- The Accessibility Service is a pure I/O module: it reads screen state and executes gestures, but holds no reasoning logic. All decisions come from Layer B.
- The MCP tool schema is versioned independently from the Hermes Agent reasoning loop, so either can evolve without breaking the other.

---

## 2. Internal / External Design

**Internal-facing (system-to-system):**
- WebSocket protocol between Layer A and Layer B — JSON command/response, request-id correlated, single persistent connection with reconnect-on-drop
- MCP tool schema — the contract the Hermes Agent calls against
- Audit log schema — internal record, not user-facing by default, but exposable in a "task history" view later

**External-facing (user-facing):**
- Consent prompt UI — session-grant model, shown once per app per session, with a visible "revoke" affordance in the persistent notification
- Task status UI — what the agent is currently doing, in plain language, not raw tool calls
- Emergency stop — a single always-reachable control (notification action + shake-to-cancel or similar) to kill the current task instantly, independent of the WebSocket round-trip

---

## 3. WebSocket Protocol Spec (design-level, not code)

Single persistent socket, JSON messages, one of three types:

| Type | Direction | Purpose |
|---|---|---|
| `command` | B → A | Agent requests an action (tap, swipe, read screen, etc.) |
| `result` | A → B | Native layer reports outcome + any screen delta |
| `event` | A → B | Unsolicited signal — consent revoked, app killed, screen locked |

Every `command` carries a `request_id`; every `result` echoes it back, so the agent loop can correlate async responses even if execution takes a beat (e.g. waiting for a screen transition).

`event` messages exist specifically so Layer A can interrupt Layer B — e.g. if the user revokes consent mid-task or locks the phone, the agent needs to hear about it without waiting for its next `command` to fail.

---

## 4. Accessibility Service Design

Three internal responsibilities, kept as separate classes so any one can be swapped or tested independently:

1. **Tree Reader** — walks the accessibility node tree, serializes to the UI-tree format the MCP `screen_read` tool returns
2. **Gesture Dispatcher** — takes a validated command (tap/swipe/long-press/pinch coordinates) and issues the corresponding `dispatchGesture` call
3. **Fallback Trigger** — decides when the tree read is insufficient (empty/sparse node tree, WebView, game surface) and requests a raw screenshot for OCR instead

This separation matters for the Phantom Process Killer hurdle: the Foreground Service that keeps the Termux core alive is a distinct component from all three of the above, so if Android throttles the service, it's diagnosable which piece failed.

---

## 5. Design Review Checklist

Before moving into Construct, confirm:

- [ ] WebSocket reconnect behavior is defined for: app backgrounded, phone locked, Termux core killed and restarted
- [ ] Consent Manager's session-grant scope is defined precisely — per app, or per app + per permission type (file read vs. screen read vs. gesture control)?
- [ ] Emergency stop path is independent of the WebSocket — confirmed it works even if Layer B is unresponsive
- [ ] Audit log write path doesn't block the agent loop (async write, not sync)
- [ ] OCR fallback trigger conditions are testable (what specifically counts as "sparse" node tree)

---

## 6. Detailed Project Development (prep for Phase 4)

Suggested build order, each a testable milestone before moving to the next:

1. Accessibility Service standalone: read a UI tree, log it to disk — no MCP, no agent yet
2. Gesture Dispatcher standalone: hardcode a tap sequence, confirm it lands correctly on a test app
3. Embed Termux core, get Foreground Service surviving 30+ min backgrounded with battery optimization on (the hurdle — de-risk this early, not last)
4. Local WebSocket bridge, both directions, with the `command`/`result`/`event` message types
5. Wire in the MCP tool schema + Hermes Agent loop, single tool first (`touch_tap`) end-to-end
6. Add remaining tools, OCR fallback, consent gates, audit logging

This mirrors the original doc's roadmap but reorders step 3 (the process-killer problem) earlier, since it's the requirement everything else depends on — no point building the full tool schema if the core gets killed in the background.
