## ADDED Requirements

### Requirement: Always-Reachable Control

The emergency stop SHALL be a single always-reachable control that kills the current task instantly.

#### Scenario: Emergency stop via notification action
- **WHEN** the user taps Stop on the notification
- **THEN** the task is terminated within 1 second

#### Scenario: Emergency stop via shake gesture (optional)
- **WHEN** the user shakes the device vigorously (configurable sensitivity, requires accelerometer polling)
- **THEN** the task is terminated within 1 second
- **NOTE**: Optional feature. Accelerometer polling consumes battery.

#### Scenario: Emergency stop via hardware button
- **WHEN** the user presses a configurable hardware button combination
- **THEN** the task is terminated within 1 second

### Requirement: Emergency Stop Independence from WebSocket

The emergency stop path MUST NOT depend on the WebSocket connection.

#### Scenario: Stop while WebSocket is connected
- **WHEN** the stop is triggered and WebSocket is connected
- **THEN** Layer A terminates locally and sends "task_killed" to Layer B

#### Scenario: Stop while WebSocket is disconnected
- **WHEN** the stop is triggered and WebSocket is disconnected
- **THEN** Layer A terminates locally without waiting

#### Scenario: Stop while Layer B is unresponsive
- **WHEN** the stop is triggered and Layer B has not responded for > 5 seconds
- **THEN** Layer A terminates locally and logs the unresponsive state

### Requirement: Emergency Stop Scope

The emergency stop SHALL terminate all agent activity.

#### Scenario: Stop terminates gesture execution
- **WHEN** the stop is triggered during a gesture
- **THEN** the gesture is cancelled and no further gestures are dispatched

#### Scenario: Stop terminates pending commands
- **WHEN** the stop is triggered with queued commands
- **THEN** all pending commands are discarded

#### Scenario: Stop sends consent_revoked event
- **WHEN** the stop is triggered
- **THEN** the consent manager revokes all grants and a consent_revoked event is sent

#### Scenario: Post-stop command rejection
- **WHEN** Layer A receives a command after emergency stop
- **THEN** Layer A rejects it with status "stopped"

### Requirement: Emergency Stop Feedback

The user SHALL receive visual feedback.

#### Scenario: Notification updates on stop
- **WHEN** the stop is triggered
- **THEN** the notification shows "Agent stopped" and replaces Stop with Restart

#### Scenario: Toast feedback on stop
- **WHEN** the stop is triggered
- **THEN** a toast says "Agent stopped" for 2 seconds

### Requirement: Emergency Stop Reset

After an emergency stop, the agent SHALL be restartable.

#### Scenario: Restart after stop
- **WHEN** the user taps Restart
- **THEN** the agent resets to idle and waits for a new task

#### Scenario: App restart after stop
- **WHEN** the user force-stops and relaunches
- **THEN** the agent starts fresh
