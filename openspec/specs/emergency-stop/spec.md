## Purpose

A single always-reachable control that kills the current task instantly. Works independently of the WebSocket round-trip — terminates activity locally in Layer A even if Layer B is unresponsive. Provides visual feedback and allows manual restart after stop.

## Requirements

### Requirement: Always-Reachable Control

The emergency stop SHALL be a single always-reachable control that kills the current task instantly. It works independently of the WebSocket round-trip and even if Layer B is unresponsive.

#### Scenario: Emergency stop via notification action
- **WHEN** the user taps "Stop" on the persistent notification
- **THEN** the current task is terminated within 1 second, regardless of WebSocket state

#### Scenario: Emergency stop via shake gesture (optional)
- **WHEN** the user shakes the device vigorously (configurable sensitivity, requires accelerometer polling)
- **THEN** the current task is terminated within 1 second
- **NOTE**: This is an optional feature. Accelerometer polling consumes battery. If disabled, only notification and hardware button triggers are available.

#### Scenario: Emergency stop via hardware button
- **WHEN** the user presses a configurable hardware button combination (e.g., volume down + power)
- **THEN** the current task is terminated within 1 second

### Requirement: Emergency Stop Independence from WebSocket

The emergency stop path MUST NOT depend on the WebSocket connection. It works even if Layer B is unresponsive or the WebSocket is disconnected.

#### Scenario: Stop while WebSocket is connected
- **WHEN** the emergency stop is triggered and the WebSocket is connected
- **THEN** Layer A terminates the current task locally and sends a "task_killed" event to Layer B

#### Scenario: Stop while WebSocket is disconnected
- **WHEN** the emergency stop is triggered and the WebSocket is disconnected
- **THEN** Layer A terminates the current task locally without waiting for WebSocket reconnection

#### Scenario: Stop while Layer B is unresponsive
- **WHEN** the emergency stop is triggered and Layer B has not responded to the last command for > 5 seconds
- **THEN** Layer A terminates the current task locally, does not wait for Layer B, and logs the unresponsive state

### Requirement: Emergency Stop Scope

The emergency stop SHALL terminate all agent activity, not just the current command.

#### Scenario: Stop terminates gesture execution
- **WHEN** the emergency stop is triggered while a gesture is being executed
- **THEN** the gesture is cancelled (if still in progress) and no further gestures are dispatched

#### Scenario: Stop terminates pending commands
- **WHEN** the emergency stop is triggered while multiple commands are queued
- **THEN** all pending commands are discarded and no further commands are executed

#### Scenario: Stop sends consent_revoked event
- **WHEN** the emergency stop is triggered
- **THEN** the consent manager revokes all active grants and a "consent_revoked" event is sent to Layer B

#### Scenario: Post-stop command rejection
- **WHEN** Layer A receives a command from Layer B after emergency stop has been triggered
- **THEN** Layer A rejects the command with status "stopped" and does not execute it

### Requirement: Emergency Stop Feedback

The user SHALL receive visual feedback that the emergency stop was activated.

#### Scenario: Notification updates on stop
- **WHEN** the emergency stop is triggered
- **THEN** the persistent notification updates to show "Agent stopped" and the "Stop" action is replaced with a "Restart" action

#### Scenario: Toast feedback on stop
- **WHEN** the emergency stop is triggered
- **THEN** a toast message is displayed saying "Agent stopped" for 2 seconds

### Requirement: Emergency Stop Reset

After an emergency stop, the agent SHALL be restartable manually.

#### Scenario: Restart after stop
- **WHEN** the user taps "Restart" on the notification after an emergency stop
- **THEN** the agent resets to idle state, consent grants are cleared, and the agent waits for a new task

#### Scenario: App restart after stop
- **WHEN** the user force-stops and relaunches the app after an emergency stop
- **THEN** the agent starts fresh with no consent grants and no pending tasks
