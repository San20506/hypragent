## ADDED Requirements

### Requirement: Session-Grant Model

Consent SHALL be granted per app and per permission type.

#### Scenario: Consent granted per app + per permission type
- **WHEN** the user grants consent for Chrome with "screen read" and "gesture control"
- **THEN** the agent can read and gesture on Chrome but not on other apps

#### Scenario: Consent does not cross apps
- **WHEN** the user grants consent for Chrome
- **THEN** the agent cannot act on Gmail until separate consent is granted

#### Scenario: Consent does not cross permission types
- **WHEN** the user grants consent for Chrome with "screen read" only
- **THEN** the agent cannot gesture on Chrome until "gesture control" is also granted

#### Scenario: Consent scope is configurable
- **WHEN** the consent manager is configured with `per_app` scope
- **THEN** a single grant covers all permission types for that app

### Requirement: Consent Prompt UI

The consent prompt SHALL be shown once per app per session.

#### Scenario: First interaction with a new app
- **WHEN** the agent attempts an action on an app with no active grant
- **THEN** the consent prompt shows with app name, permissions, and Allow/Deny buttons

#### Scenario: Consent already granted
- **WHEN** the agent attempts an action on an app with an active grant
- **THEN** the prompt is not shown

#### Scenario: User denies consent
- **WHEN** the user taps Deny
- **THEN** no grant is created and the prompt is not shown again for this app in this session

#### Scenario: User allows consent
- **WHEN** the user taps Allow
- **THEN** a session grant is created and the action proceeds

#### Scenario: Concurrent consent prompts
- **WHEN** the agent attempts actions on multiple apps simultaneously
- **THEN** the consent manager queues prompts sequentially and the agent blocks on queued actions until consent is granted or denied

### Requirement: Consent Revocation

The user SHALL be able to revoke consent at any time.

#### Scenario: Revoke via notification action
- **WHEN** the user taps Revoke Consent
- **THEN** all grants are revoked, the agent receives a consent_revoked event, and in-progress tasks are terminated

#### Scenario: Revoke while task is running
- **WHEN** consent is revoked during a task
- **THEN** the task is interrupted within 1 second

#### Scenario: Revoke does not affect future sessions
- **WHEN** consent is revoked
- **THEN** the next launch starts with no grants

### Requirement: Consent Grant Storage

Consent grants SHALL be stored in memory only.

#### Scenario: Grants are in-memory only
- **WHEN** the app is restarted
- **THEN** all previous grants are gone

#### Scenario: Grants are cleared on session end
- **WHEN** the foreground service stops
- **THEN** all grants are cleared

#### Scenario: Grants survive app backgrounding
- **WHEN** the app is backgrounded
- **THEN** grants remain active

### Requirement: Consent Manager Integration with Emergency Stop

The emergency stop SHALL revoke consent as part of its shutdown.

#### Scenario: Emergency stop revokes consent
- **WHEN** the emergency stop is triggered
- **THEN** the consent manager revokes all grants and the agent stops immediately
