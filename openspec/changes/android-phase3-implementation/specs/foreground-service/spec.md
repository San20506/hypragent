## ADDED Requirements

### Requirement: Foreground Service Lifecycle

A foreground service SHALL keep the Termux core process alive in the background.

#### Scenario: Service starts on app launch
- **WHEN** the HYPR Agent app is launched
- **THEN** the foreground service starts and displays a persistent notification

#### Scenario: Service survives backgrounding
- **WHEN** the user backgrounds the app
- **THEN** the foreground service continues running

#### Scenario: Service survives screen lock
- **WHEN** the user locks the phone screen
- **THEN** the foreground service continues running

#### Scenario: Service survives battery optimization
- **WHEN** the device has battery optimization enabled
- **THEN** the foreground service continues running for at least 30 minutes

#### Scenario: Service restart after kill
- **WHEN** the foreground service is killed by the system
- **THEN** the service attempts to restart within 5 seconds using `START_STICKY`

### Requirement: Termux Core Embedding

The Termux core SHALL run inside the foreground service as a child process.

#### Scenario: Termux core starts within service
- **WHEN** the foreground service starts
- **THEN** the Termux core process initializes within 5 seconds and the MCP server becomes reachable

#### Scenario: Termux core embedding mechanism
- **WHEN** the foreground service starts the Termux core
- **THEN** it launches the Termux core as a child process using the Termux:Plugin API or a bundled bootstrap

#### Scenario: Termux core health check
- **WHEN** the foreground service is running
- **THEN** it performs a health check every 30 seconds

#### Scenario: Termux core process dies
- **WHEN** the Termux core crashes
- **THEN** the foreground service detects the failure within 30 seconds and restarts it

#### Scenario: Termux core restart fails 3 times
- **WHEN** the Termux core fails to start 3 consecutive times
- **THEN** the foreground service logs the failure, notifies the user, and stops retrying

### Requirement: Persistent Notification

The foreground service SHALL display a persistent notification with status and controls.

#### Scenario: Notification shows agent status
- **WHEN** the foreground service is running
- **THEN** the notification displays the current agent status

#### Scenario: Notification includes revoke action
- **WHEN** consent is granted
- **THEN** the notification includes a "Revoke Consent" button

#### Scenario: Notification includes emergency stop
- **WHEN** a task is active
- **THEN** the notification includes a "Stop" button

#### Scenario: Notification is not dismissible
- **WHEN** the foreground service is running
- **THEN** the notification cannot be swiped away

### Requirement: Phantom Process Killer Resilience

The foreground service SHALL survive Android's Phantom Process Killer.

#### Scenario: Service classified as foreground
- **WHEN** the foreground service is running with a persistent notification
- **THEN** Android does not apply Phantom Process Killer rules

#### Scenario: Termux child process protection
- **WHEN** the Termux core runs as a child process
- **THEN** it is protected as long as the foreground service is alive

#### Scenario: OomAdj score monitoring
- **WHEN** the foreground service is running
- **THEN** its OomAdj score remains at FOREGROUND_SERVICE level
