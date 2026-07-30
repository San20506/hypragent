## Purpose

Manages user consent with a session-grant model scoped per app and per permission type. Shows a consent prompt once per app per session, provides revoke affordance via the persistent notification, and stores grants in memory only (no disk persistence). Integrates with the emergency stop to revoke all grants on kill.

## Requirements

### Requirement: Session-Grant Model

Consent SHALL be granted per app and per permission type. A session grant allows the agent to perform specific actions on a specific app until revoked or the session ends.

#### Scenario: Consent granted per app + per permission type
- **WHEN** the user grants consent for Chrome with "screen read" and "gesture control" permissions
- **THEN** the agent can read the screen and perform gestures on Chrome, but cannot read files or perform other permission types on Chrome

#### Scenario: Consent does not cross apps
- **WHEN** the user grants consent for Chrome
- **THEN** the agent cannot perform any actions on Gmail until separate consent is granted for Gmail

#### Scenario: Consent does not cross permission types
- **WHEN** the user grants consent for Chrome with "screen read" permission
- **THEN** the agent can read Chrome's screen but cannot perform gestures on Chrome until "gesture control" is also granted

#### Scenario: Consent scope is configurable
- **WHEN** the consent manager is configured with a permission scope of `per_app` (not `per_app_per_type`)
- **THEN** a single grant for an app covers all permission types for that app

### Requirement: Consent Prompt UI

The consent prompt SHALL be shown once per app per session. It clearly states what the agent wants to do and with which app.

#### Scenario: First interaction with a new app
- **WHEN** the agent attempts to perform an action on an app that has no active consent grant
- **THEN** the consent prompt UI is displayed showing the app name, requested permissions, and "Allow" / "Deny" buttons

#### Scenario: Consent already granted
- **WHEN** the agent attempts to perform an action on an app that has an active consent grant
- **THEN** the consent prompt is not shown and the action proceeds immediately

#### Scenario: User denies consent
- **WHEN** the user taps "Deny" on the consent prompt
- **THEN** no consent grant is created, the agent receives a "consent denied" error, and the prompt is not shown again for this app in this session

#### Scenario: User allows consent
- **WHEN** the user taps "Allow" on the consent prompt
- **THEN** a session grant is created for the specified app and permission types, and the agent proceeds with the action

#### Scenario: Concurrent consent prompts
- **WHEN** the agent attempts to perform actions on multiple apps simultaneously (e.g., Chrome and Gmail in a parallel batch)
- **THEN** the consent manager queues the prompts and shows them sequentially (one at a time), and the agent blocks on the queued actions until consent is granted or denied for each

### Requirement: Consent Revocation

The user SHALL be able to revoke consent at any time via a visible affordance in the persistent notification.

#### Scenario: Revoke via notification action
- **WHEN** the user taps "Revoke Consent" on the persistent notification
- **THEN** all active consent grants are revoked immediately, the agent receives a "consent revoked" event, and any in-progress task is terminated

#### Scenario: Revoke while task is running
- **WHEN** the user revokes consent while a task is in progress
- **THEN** the current task is interrupted within 1 second, the agent sends a "consent revoked" event to Layer B, and the agent stops all actions on all apps

#### Scenario: Revoke does not affect future sessions
- **WHEN** consent is revoked in the current session
- **THEN** the next app launch starts with no grants and the consent prompt will be shown again for each app

### Requirement: Consent Grant Storage

Consent grants SHALL be stored in memory only, not persisted to disk. This ensures grants do not survive app restarts.

#### Scenario: Grants are in-memory only
- **WHEN** the app is restarted
- **THEN** all previous consent grants are gone and the consent prompt will be shown again

#### Scenario: Grants are cleared on session end
- **WHEN** the foreground service stops (app killed or user force-stops)
- **THEN** all consent grants are cleared from memory

#### Scenario: Grants survive app backgrounding
- **WHEN** the app is backgrounded (not killed)
- **THEN** consent grants remain active in memory and the agent can continue actions without re-prompting

### Requirement: Consent Manager Integration with Emergency Stop

The emergency stop mechanism SHALL revoke consent as part of its shutdown sequence.

#### Scenario: Emergency stop revokes consent
- **WHEN** the emergency stop is triggered
- **THEN** the consent manager revokes all active grants and the agent stops immediately
