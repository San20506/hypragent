## ADDED Requirements

### Requirement: Plain Language Status Display

The task status UI SHALL show the current action in plain language.

#### Scenario: Status shows current action
- **WHEN** the agent is executing a task
- **THEN** the UI displays the action in plain language (e.g., "Reading screen...", "Tapping button...")

#### Scenario: Status updates on each step
- **WHEN** the agent completes one step
- **THEN** the UI updates within 1 second

#### Scenario: Status shows task progress
- **WHEN** the agent is executing a multi-step task
- **THEN** the UI shows the current step number without a total (e.g., "Step 3")

#### Scenario: Status shows idle state
- **WHEN** no task is running
- **THEN** the UI displays "Idle" or "Waiting for task..."

### Requirement: Status Location

The status SHALL be in a persistent, always-visible location.

#### Scenario: Status in notification
- **WHEN** the foreground service is running
- **THEN** the notification shows the current status

#### Scenario: Status in overlay (optional)
- **WHEN** the overlay is enabled
- **THEN** a semi-transparent overlay shows the status at the top of the screen

#### Scenario: Status overlay does not block interaction
- **WHEN** the overlay is displayed
- **THEN** touch events pass through

### Requirement: Status Content

The status message SHALL be concise and jargon-free.

#### Scenario: Tool call mapped to plain language
- **WHEN** the agent executes `screen_read`
- **THEN** the status shows "Reading screen..."

#### Scenario: Gesture mapped to plain language
- **WHEN** the agent executes `tap`
- **THEN** the status shows "Tapping..."

#### Scenario: OCR mapped to plain language
- **WHEN** the agent executes OCR
- **THEN** the status shows "Extracting text from screen..."

#### Scenario: File operation mapped to plain language
- **WHEN** the agent executes `file_read`
- **THEN** the status shows "Reading file..."

#### Scenario: Error status
- **WHEN** the agent encounters an error
- **THEN** the status shows "Error: [brief description]"

### Requirement: Status History

The status UI SHALL maintain a brief history.

#### Scenario: Last 5 actions visible
- **WHEN** the agent has executed 10 actions
- **THEN** the UI shows the last 5 in reverse order

#### Scenario: Action history clears on new task
- **WHEN** a new task starts
- **THEN** the previous history is cleared
