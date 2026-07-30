## ADDED Requirements

### Requirement: Append-Only Audit Log

Every agent action SHALL be written to an append-only JSON log.

#### Scenario: Log entry for every command
- **WHEN** the agent sends a command
- **THEN** a log entry is written with timestamp, request_id, action, parameters, result

#### Scenario: Log entry for consent events
- **WHEN** consent is granted, denied, or revoked
- **THEN** a log entry is written with timestamp, event type, app package, permission types

#### Scenario: Log entry for emergency stop
- **WHEN** the emergency stop is triggered
- **THEN** a log entry is written with timestamp, event type, task state

#### Scenario: Log entry for agent errors
- **WHEN** the agent encounters an error
- **THEN** a log entry is written with timestamp, error type, message, context

#### Scenario: Cross-layer event logging
- **WHEN** Layer A sends a consent or emergency stop event to Layer B via WebSocket
- **THEN** Layer B writes a log entry for the event

### Requirement: Non-Blocking Write Path

The audit log write path MUST NOT block the agent loop.

#### Scenario: Async write does not block agent
- **WHEN** the agent writes a log entry
- **THEN** the write is async and the agent continues

#### Scenario: Write failure does not crash agent
- **WHEN** the write fails
- **THEN** the agent continues and the failure is logged to logcat

#### Scenario: Write queue with backpressure
- **WHEN** writes exceed disk throughput
- **THEN** the queue buffers 1000 entries, then drops oldest with a warning

### Requirement: Log Entry Schema

Each log entry SHALL follow a consistent JSON schema.

#### Scenario: Standard entry fields
- **WHEN** a log entry is written
- **THEN** it contains: timestamp (ISO 8601), request_id (UUID), action, parameters, result, status, duration_ms

#### Scenario: Consent event entry fields
- **WHEN** a consent event is logged
- **THEN** it contains: timestamp, event, app_package, permission_types

#### Scenario: Error entry fields
- **WHEN** an error is logged
- **THEN** it contains: timestamp, error_type, error_message, context

### Requirement: Log File Management

The audit log file SHALL be managed to prevent unbounded growth.

#### Scenario: Log file rotation
- **WHEN** the file exceeds 10 MB
- **THEN** it is rotated and a new file is created

#### Scenario: Maximum log files retained
- **WHEN** rotation creates a new file
- **THEN** the 5 most recent files are retained

#### Scenario: Log file location
- **WHEN** the log is written
- **THEN** it writes to the configured path (default: `/data/data/com.hypragent/files/audit/audit.log`)

### Requirement: Log Integrity

The append-only nature of the log SHALL be enforced.

#### Scenario: No truncation or modification
- **WHEN** a log entry is written
- **THEN** it is appended; no existing entries are modified

#### Scenario: Log file is not deletable by agent
- **WHEN** the agent runs
- **THEN** it cannot delete or rename the log file

#### Scenario: Log entry is atomic
- **WHEN** a log entry is written
- **THEN** it is written in a single operation
