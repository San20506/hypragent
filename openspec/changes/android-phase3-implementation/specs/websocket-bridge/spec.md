## ADDED Requirements

### Requirement: WebSocket Connection Establishment

Layer B SHALL act as the WebSocket server on 127.0.0.1; Layer A SHALL connect as a client.

#### Scenario: Connection on app launch
- **WHEN** the foreground service starts and the Termux core is initialized
- **THEN** Layer B starts a WebSocket server on 127.0.0.1 (default port 12345) and Layer A connects as a client

#### Scenario: Connection is single and persistent
- **WHEN** the WebSocket connection is established
- **THEN** only one connection exists at a time

#### Scenario: Connection failure on startup
- **WHEN** the Termux core is not ready
- **THEN** Layer A retries every 2 seconds for up to 30 seconds

### Requirement: Command Message Protocol

Layer B SHALL send `command` messages to Layer A. Each command carries a `request_id`.

#### Scenario: Valid command with request_id
- **WHEN** Layer B sends a command with a unique `request_id`, `action`, and parameters
- **THEN** Layer A executes the action and sends back a `result` with the same `request_id`

#### Scenario: Command action types
- **WHEN** Layer B sends a command
- **THEN** the `action` is one of: `tap`, `swipe`, `long_press`, `pinch`, `read_screen`, `screenshot`, `ocr`

#### Scenario: Command with invalid action
- **WHEN** Layer B sends an unrecognized action
- **THEN** Layer A returns `status: "error"` with `error: "unknown action"`

#### Scenario: Command with missing request_id
- **WHEN** Layer B sends a command without `request_id`
- **THEN** Layer A ignores it and logs a warning

### Requirement: Result Message Protocol

Layer A SHALL send `result` messages echoing the `request_id`.

#### Scenario: Successful result
- **WHEN** Layer A executes a command successfully
- **THEN** it sends `status: "ok"` with the result payload

#### Scenario: Failed result
- **WHEN** Layer A fails to execute a command
- **THEN** it sends `status: "error"` with the failure reason

#### Scenario: Result with screen delta
- **WHEN** Layer A executes a command that changes screen state
- **THEN** the result includes a `screen_delta` field

### Requirement: Event Message Protocol

Layer A SHALL send unsolicited `event` messages for state changes.

#### Scenario: Consent revoked event
- **WHEN** the user revokes consent
- **THEN** Layer A sends `type: "consent_revoked"` and Layer B stops the task

#### Scenario: App killed event
- **WHEN** the target app is killed
- **THEN** Layer A sends `type: "app_killed"` with `app_package`

#### Scenario: Screen locked event
- **WHEN** the user locks the screen
- **THEN** Layer A sends `type: "screen_locked"` and Layer B pauses

#### Scenario: Screen unlocked event
- **WHEN** the user unlocks the screen
- **THEN** Layer A sends `type: "screen_unlocked"` and Layer B resumes

### Requirement: Reconnect Behavior

The WebSocket connection MUST handle disconnections gracefully.

#### Scenario: App backgrounded
- **WHEN** the app is backgrounded and the connection drops
- **THEN** Layer A reconnects every 2 seconds for up to 60 seconds; only read-only commands are re-issued; non-idempotent commands are discarded

#### Scenario: Phone locked
- **WHEN** the phone is locked and the connection drops
- **THEN** Layer A reconnects in the background; restored within 5 seconds of unlock

#### Scenario: Termux core killed and restarted
- **WHEN** the Termux core is killed and restarted
- **THEN** Layer A establishes a new connection within 10 seconds and discards old pending commands

#### Scenario: Reconnect gives up
- **WHEN** reconnection fails after the maximum retry period
- **THEN** Layer A logs the failure, notifies the user, and stops

### Requirement: Request-ID Correlation

Every command SHALL carry a `request_id`; every result SHALL echo it.

#### Scenario: Request-id is a UUID
- **WHEN** Layer B generates a command
- **THEN** the `request_id` is a UUID v4 string

#### Scenario: Result echoes request_id
- **WHEN** Layer A sends a result
- **THEN** the `request_id` matches the original command

#### Scenario: Unknown request_id
- **WHEN** Layer A receives a result with no matching pending command
- **THEN** it logs a warning and discards the result

#### Scenario: Duplicate request_id
- **WHEN** Layer B receives two results with the same `request_id`
- **THEN** it uses only the first and logs a warning

#### Scenario: Screen state staleness detection
- **WHEN** Layer A receives a command and the screen state differs from the last read
- **THEN** Layer A includes `screen_changed: true` in the result

#### Scenario: WebSocket message size limit
- **WHEN** a message exceeds 1MB
- **THEN** the sender chunks it or returns a size limit error

#### Scenario: WebSocket heartbeat keepalive
- **WHEN** no message is exchanged for 30 seconds
- **THEN** either side sends a ping/pong; if no pong within 10 seconds, the connection is considered dead
