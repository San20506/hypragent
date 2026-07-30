## Purpose

Keeps the Termux core process alive in the background via an Android foreground service with persistent notification. Embeds the Termux core, runs health checks, and survives the Phantom Process Killer. Runs as a distinct component from the Accessibility Service so failures are diagnosable.

## Requirements

### Requirement: Foreground Service Lifecycle

A foreground service SHALL keep the Termux core process alive in the background. It runs as a distinct component from the accessibility service, so if Android throttles the service, it is diagnosable which piece failed.

#### Scenario: Service starts on app launch
- **WHEN** the HYPR Agent app is launched
- **THEN** the foreground service starts and displays a persistent notification with the agent status

#### Scenario: Service survives backgrounding
- **WHEN** the user backgrounds the HYPR Agent app (home screen, switch to another app)
- **THEN** the foreground service continues running and the Termux core remains alive

#### Scenario: Service survives screen lock
- **WHEN** the user locks the phone screen
- **THEN** the foreground service continues running and the Termux core remains alive

#### Scenario: Service survives battery optimization
- **WHEN** the device has battery optimization enabled for the HYPR Agent app
- **THEN** the foreground service continues running for at least 30 minutes in the background

#### Scenario: Service restart after kill
- **WHEN** the foreground service is killed by the system (e.g., extreme memory pressure)
- **THEN** the service attempts to restart within 5 seconds using `START_STICKY` behavior

### Requirement: Termux Core Embedding

The Termux core SHALL run inside the foreground service and host the Hermes Agent reasoning loop, MCP server, and AI backend adapter.

#### Scenario: Termux core starts within service
- **WHEN** the foreground service starts
- **THEN** the Termux core process initializes within 5 seconds and the MCP server becomes reachable

#### Scenario: Termux core embedding mechanism
- **WHEN** the foreground service starts the Termux core
- **THEN** it launches the Termux core as a child process using the Termux:Plugin API or a bundled Termux bootstrap, and the process runs within the app's private data directory

#### Scenario: Termux core process health check
- **WHEN** the foreground service is running
- **THEN** it performs a health check on the Termux core process every 30 seconds

#### Scenario: Termux core process dies
- **WHEN** the Termux core process crashes or is killed
- **THEN** the foreground service detects the failure within 30 seconds and attempts to restart the Termux core

#### Scenario: Termux core restart fails 3 times
- **WHEN** the Termux core fails to start 3 consecutive times
- **THEN** the foreground service logs the failure, sends a notification to the user, and stops retrying until manually restarted

### Requirement: Persistent Notification

The foreground service SHALL display a persistent notification that shows agent status and provides controls.

#### Scenario: Notification shows agent status
- **WHEN** the foreground service is running
- **THEN** the notification displays the current agent status (e.g., "Idle", "Processing task...", "Consent granted for Chrome")

#### Scenario: Notification includes revoke action
- **WHEN** the foreground service is running and consent is granted
- **THEN** the notification includes a "Revoke Consent" action button that revokes all active grants

#### Scenario: Notification includes emergency stop
- **WHEN** the foreground service is running and a task is active
- **THEN** the notification includes a "Stop" action button that immediately terminates the current task

#### Scenario: Notification is not dismissible
- **WHEN** the foreground service is running
- **THEN** the notification cannot be swiped away by the user (persistent notification requirement)

### Requirement: Phantom Process Killer Resilience

Android's Phantom Process Killer terminates background processes that consume too many resources. The foreground service SHALL survive this.

#### Scenario: Service classified as foreground
- **WHEN** the foreground service is running with a persistent notification
- **THEN** Android classifies it as a foreground service and does not apply Phantom Process Killer rules

#### Scenario: Termux child process protection
- **WHEN** the Termux core runs as a child process of the foreground service
- **THEN** it is protected from the Phantom Process Killer as long as the foreground service is alive

#### Scenario: OomAdj score monitoring
- **WHEN** the foreground service is running
- **THEN** its OomAdj score remains at FOREGROUND_SERVICE level (not degraded to cached/background)
