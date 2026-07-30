## Purpose

A single persistent local WebSocket connection on 127.0.0.1 bridges Layer A (Native Android App) and Layer B (Embedded Termux Core). JSON command/result/event messages flow in both directions with request-id correlation and reconnect behavior for three failure modes: app backgrounded, phone locked, and Termux core killed.

## Requirements

### Requirement: WebSocket Connection Establishment

A single persistent local WebSocket connection (127.0.0.1) SHALL bridge Layer A (Native Android App) and Layer B (Embedded Termux Core). JSON messages flow in both directions.

#### Scenario: Connection on app launch
- **WHEN** the foreground service starts and the Termux core is initialized
- **THEN** Layer B (Termux core) starts a WebSocket server on 127.0.0.1 with a configurable port (default: 12345), and Layer A (native app) connects as a client

#### Scenario: Connection is single and persistent
- **WHEN** the WebSocket connection is established
- **THEN** only one connection exists at a time; new commands reuse the existing connection

#### Scenario: Connection failure on startup
- **WHEN** the Termux core is not ready when the native app attempts to connect
- **THEN** Layer A retries the connection every 2 seconds for up to 30 seconds before reporting failure

### Requirement: Command Message Protocol

Layer B SHALL send `command` messages to Layer A requesting actions (tap, swipe, read screen, etc.). Each command carries a `request_id` for correlation.

#### Scenario: Valid command with request_id
- **WHEN** Layer B sends a command message with a unique `request_id`, `action` type, and parameters
- **THEN** Layer A receives the message, executes the action, and sends back a `result` message with the same `request_id`

#### Scenario: Command action types
- **WHEN** Layer B sends a command message
- **THEN** the `action` field is one of: `tap`, `swipe`, `long_press`, `pinch`, `read_screen`, `screenshot`, `ocr`

#### Scenario: Command with invalid action
- **WHEN** Layer B sends a command with an unrecognized `action` type
- **THEN** Layer A returns a `result` message with `request_id` matching, `status: "error"`, and `error: "unknown action"`

#### Scenario: Command with missing request_id
- **WHEN** Layer B sends a command without a `request_id` field
- **THEN** Layer A ignores the message and logs a warning

### Requirement: Result Message Protocol

Layer A SHALL send `result` messages back to Layer B reporting the outcome of a command. Every result echoes the `request_id` from the original command.

#### Scenario: Successful result
- **WHEN** Layer A executes a command successfully
- **THEN** it sends a `result` message with the same `request_id`, `status: "ok"`, and the result payload (e.g., screen data, gesture confirmation)

#### Scenario: Failed result
- **WHEN** Layer A fails to execute a command (e.g., gesture failed, screen read error)
- **THEN** it sends a `result` message with the same `request_id`, `status: "error"`, and an `error` field with the failure reason

#### Scenario: Result with screen delta
- **WHEN** Layer A executes a command that changes screen state (e.g., tap navigates to new screen)
- **THEN** the `result` message includes a `screen_delta` field with the new screen state (node tree or screenshot)

### Requirement: Event Message Protocol

Layer A SHALL send unsolicited `event` messages to Layer B for state changes that are not responses to commands.

#### Scenario: Consent revoked event
- **WHEN** the user revokes consent via the notification action
- **THEN** Layer A sends an `event` message with `type: "consent_revoked"` and Layer B immediately stops the current task

#### Scenario: App killed event
- **WHEN** the target app being controlled is killed by the user or system
- **THEN** Layer A sends an `event` message with `type: "app_killed"` and the `app_package` field

#### Scenario: Screen locked event
- **WHEN** the user locks the phone screen
- **THEN** Layer A sends an `event` message with `type: "screen_locked"` and Layer B pauses the current task

#### Scenario: Screen unlocked event
- **WHEN** the user unlocks the phone screen
- **THEN** Layer A sends an `event` message with `type: "screen_unlocked"` and Layer B resumes if it was paused

### Requirement: Reconnect Behavior

The WebSocket connection MUST handle disconnections gracefully across three failure modes.

#### Scenario: App backgrounded
- **WHEN** the native app is backgrounded and the WebSocket connection drops
- **THEN** Layer A attempts to reconnect every 2 seconds for up to 60 seconds; if the connection is restored, only read-only commands (screen_read, screenshot, ocr) are re-issued; non-idempotent commands (tap, swipe, keyboard_type) are discarded with a warning

#### Scenario: Phone locked
- **WHEN** the phone is locked and the WebSocket connection drops
- **THEN** Layer A maintains the connection attempt in the background; when the phone is unlocked, the connection is restored within 5 seconds

#### Scenario: Termux core killed and restarted
- **WHEN** the Termux core process is killed and restarted by the foreground service
- **THEN** Layer A detects the old connection is dead, establishes a new connection to the restarted Termux core within 10 seconds, and discards any pending commands from the old session

#### Scenario: Reconnect gives up
- **WHEN** the WebSocket connection cannot be re-established after the maximum retry period
- **THEN** Layer A logs the failure, sends a notification to the user, and stops sending commands until manually restarted

### Requirement: Request-ID Correlation

Every command SHALL carry a `request_id`; every result SHALL echo it back. This allows the agent loop to correlate async responses.

#### Scenario: Request-id is a UUID
- **WHEN** Layer B generates a command
- **THEN** the `request_id` is a UUID v4 string

#### Scenario: Result echoes request_id
- **WHEN** Layer A sends a result message
- **THEN** the `request_id` field matches the original command's `request_id` exactly

#### Scenario: Unknown request_id
- **WHEN** Layer A receives a result with a `request_id` that does not match any pending command
- **THEN** Layer A logs a warning and discards the result

#### Scenario: Duplicate request_id
- **WHEN** Layer B receives two result messages with the same `request_id`
- **THEN** Layer B uses only the first result and logs a warning for the duplicate

#### Scenario: Screen state staleness detection
- **WHEN** Layer A receives a command and the current screen state differs from the state the agent last read (e.g., notification appeared, dialog opened, screen rotated)
- **THEN** Layer A includes a `screen_changed: true` flag in the result message so the agent knows it may be acting on stale data

#### Scenario: WebSocket message size limit
- **WHEN** a WebSocket message exceeds the configured size limit (default: 1MB)
- **THEN** the sender chunks the message or returns a size limit error, and the receiver logs a warning

#### Scenario: WebSocket heartbeat keepalive
- **WHEN** no message is exchanged for 30 seconds
- **THEN** either side sends a ping/pong frame to verify connection liveness, and if no pong is received within 10 seconds, the connection is considered dead and reconnect behavior begins
