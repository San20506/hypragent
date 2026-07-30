## Purpose

Append-only JSON audit log of every agent action. Writes are asynchronous and non-blocking to the agent loop. Includes log rotation, integrity enforcement, and a consistent entry schema. Internal by default, exposable in a future task history view.

## Requirements

### Requirement: Append-Only Audit Log

Every action taken by the agent SHALL be written to an append-only JSON log. The log is internal, not user-facing by default, but exposable in a "task history" view later.

#### Scenario: Log entry for every command
- **WHEN** the agent sends a command via WebSocket
- **THEN** a log entry is written with timestamp, request_id, action type, parameters, and result

#### Scenario: Log entry for consent events
- **WHEN** consent is granted, denied, or revoked
- **THEN** a log entry is written with timestamp, event type, app package, and permission types

#### Scenario: Log entry for emergency stop
- **WHEN** the emergency stop is triggered
- **THEN** a log entry is written with timestamp, event type "emergency_stop", and the task state at time of stop

#### Scenario: Log entry for agent errors
- **WHEN** the agent encounters an error (command failure, backend error, etc.)
- **THEN** a log entry is written with timestamp, error type, error message, and context

#### Scenario: Cross-layer event logging
- **WHEN** Layer A sends a consent or emergency stop event to Layer B via WebSocket
- **THEN** Layer B writes a log entry for the event with timestamp, event type, and source (Layer A)

### Requirement: Non-Blocking Write Path

The audit log write path MUST NOT block the agent loop. Writes are asynchronous.

#### Scenario: Async write does not block agent
- **WHEN** the agent needs to write a log entry
- **THEN** the write is dispatched asynchronously and the agent continues executing without waiting for the write to complete

#### Scenario: Write failure does not crash agent
- **WHEN** the log write fails (disk full, permission error, etc.)
- **THEN** the agent continues executing and the failure is logged to a separate error output (e.g., logcat)

#### Scenario: Write queue with backpressure
- **WHEN** log writes are generated faster than disk can persist them
- **THEN** the write queue buffers up to 1000 entries, then drops oldest entries with a warning

### Requirement: Log Entry Schema

Each log entry SHALL follow a consistent JSON schema.

#### Scenario: Standard entry fields
- **WHEN** a log entry is written
- **THEN** it contains: `timestamp` (ISO 8601), `request_id` (UUID), `action` (string), `parameters` (object), `result` (object), `status` (ok/error), `duration_ms` (integer)

#### Scenario: Consent event entry fields
- **WHEN** a consent event is logged
- **THEN** it contains: `timestamp`, `event` (granted/denied/revoked), `app_package` (string), `permission_types` (array of strings)

#### Scenario: Error entry fields
- **WHEN** an error is logged
- **THEN** it contains: `timestamp`, `error_type` (string), `error_message` (string), `context` (object with request_id, action, etc.)

### Requirement: Log File Management

The audit log file SHALL be managed to prevent unbounded growth.

#### Scenario: Log file rotation
- **WHEN** the audit log file exceeds 10 MB
- **THEN** the file is rotated: the current file is renamed with a timestamp suffix and a new empty file is created

#### Scenario: Maximum log files retained
- **WHEN** log rotation creates a new file
- **THEN** the 5 most recent log files are retained and older files are deleted

#### Scenario: Log file location
- **WHEN** the audit log is written
- **THEN** it writes to the configured path (default: `/data/data/com.hypragent/files/audit/audit.log`)

### Requirement: Log Integrity

The append-only nature of the log SHALL be enforced.

#### Scenario: No truncation or modification
- **WHEN** a log entry is written
- **THEN** it is appended to the end of the file; no existing entries are modified or truncated

#### Scenario: Log file is not deletable by agent
- **WHEN** the agent runs
- **THEN** it cannot delete or rename the audit log file (file permission enforcement)

#### Scenario: Log entry is atomic
- **WHEN** a log entry is written
- **THEN** the entry is written in a single write operation (no partial entries on crash)
