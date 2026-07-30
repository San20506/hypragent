## Purpose

User-facing UI that shows what the agent is currently doing in plain language (not raw tool calls). Displayed in the persistent notification and optionally as a semi-transparent overlay. Maps tool calls to human-readable descriptions and maintains a brief action history.

## Requirements

### Requirement: Plain Language Status Display

The task status UI SHALL show what the agent is currently doing in plain language, not raw tool calls. It is user-facing and designed for non-technical users.

#### Scenario: Status shows current action
- **WHEN** the agent is executing a task
- **THEN** the status UI displays the current action in plain language (e.g., "Reading screen...", "Tapping button...", "Typing text...")

#### Scenario: Status updates on each step
- **WHEN** the agent completes one step and starts the next
- **THEN** the status UI updates to reflect the new action within 1 second

#### Scenario: Status shows task progress
- **WHEN** the agent is executing a multi-step task
- **THEN** the status UI shows the current step number without a total (e.g., "Step 3") since the total is unknown until task completion

#### Scenario: Status shows idle state
- **WHEN** the agent is not executing any task
- **THEN** the status UI displays "Idle" or "Waiting for task..."

### Requirement: Status Location

The status SHALL be displayed in a persistent, always-visible location.

#### Scenario: Status in notification
- **WHEN** the foreground service is running
- **THEN** the persistent notification shows the current agent status in its content area

#### Scenario: Status in overlay (optional)
- **WHEN** the status overlay is enabled in configuration
- **THEN** a semi-transparent overlay is displayed at the top of the screen showing the current agent status

#### Scenario: Status overlay does not block interaction
- **WHEN** the status overlay is displayed
- **THEN** the user can still interact with the screen through the overlay (touch events pass through)

### Requirement: Status Content

The status message SHALL be concise and avoid technical jargon.

#### Scenario: Tool call mapped to plain language
- **WHEN** the agent executes a `screen_read` tool call
- **THEN** the status shows "Reading screen..." (not "Executing screen_read tool")

#### Scenario: Gesture mapped to plain language
- **WHEN** the agent executes a `tap` tool call at coordinates (500, 300)
- **THEN** the status shows "Tapping..." (not "Executing tap at (500, 300)")

#### Scenario: OCR mapped to plain language
- **WHEN** the agent executes an OCR tool call
- **THEN** the status shows "Extracting text from screen..." (not "Running tesseract OCR")

#### Scenario: File operation mapped to plain language
- **WHEN** the agent executes a `file_read` tool call
- **THEN** the status shows "Reading file..." (not "Executing file_read on /path/to/file")

#### Scenario: Error status
- **WHEN** the agent encounters an error during task execution
- **THEN** the status shows "Error: [brief description]" (e.g., "Error: Could not tap button")

### Requirement: Status History

The status UI SHALL maintain a brief history of recent actions.

#### Scenario: Last 5 actions visible
- **WHEN** the agent has executed 10 actions
- **THEN** the status UI shows the last 5 actions in reverse chronological order (most recent first)

#### Scenario: Action history clears on new task
- **WHEN** a new task starts
- **THEN** the action history from the previous task is cleared
