## ADDED Requirements

### Requirement: Android-Native MCP Tool Schema

The MCP tool schema SHALL define Android-native tools, versioned independently from the agent loop.

#### Scenario: Tool schema versioned independently
- **WHEN** the schema is updated
- **THEN** the agent loop continues with the old schema until restarted

#### Scenario: Tool schema includes screen_read
- **WHEN** the MCP server starts
- **THEN** the schema includes `screen_read` with optional region and output format

#### Scenario: Tool schema includes gesture tools
- **WHEN** the MCP server starts
- **THEN** the schema includes `tap`, `swipe`, `long_press`, `pinch` with coordinates

#### Scenario: Tool schema includes OCR tool
- **WHEN** the MCP server starts
- **THEN** the schema includes `read_screen_text` with optional region

#### Scenario: Tool schema includes file operations
- **WHEN** the MCP server starts
- **THEN** the schema includes `file_read`, `file_write`, `file_list`, `file_move`, `file_delete`

#### Scenario: Tool schema includes terminal execution
- **WHEN** the MCP server starts
- **THEN** the schema includes `termux_exec` with command and timeout

### Requirement: Hermes Agent Reasoning Loop

The Hermes Agent SHALL execute the perceive-reason-act cycle in Layer B.

#### Scenario: Full agent cycle
- **WHEN** the agent receives a task
- **THEN** it executes: read screen -> reason -> send command -> receive result -> repeat until done or max steps

#### Scenario: Agent uses screen_read
- **WHEN** the agent needs screen state
- **THEN** it sends `screen_read` via WebSocket

#### Scenario: Agent uses gesture tools
- **WHEN** the agent decides to act
- **THEN** it sends the gesture command via WebSocket

#### Scenario: Agent handles command failure
- **WHEN** a command returns error
- **THEN** the agent logs it, reasons about it, and decides retry/alternative/failure

#### Scenario: Agent respects max steps
- **WHEN** the agent reaches max steps (default: 20)
- **THEN** it stops and reports "max steps reached"

#### Scenario: Agent responds to consent_revoked
- **WHEN** the agent receives consent_revoked
- **THEN** it stops immediately and reports "consent revoked"

### Requirement: AI Backend Adapter

The adapter SHALL support Claude, Gemini, and Ollama, swappable via config.

#### Scenario: Backend selected by configuration
- **WHEN** config specifies `backend.active: claude`
- **THEN** the agent uses Claude

#### Scenario: Backend swap without code change
- **WHEN** config changes from claude to gemini
- **THEN** the agent uses Gemini after restart

#### Scenario: Backend sends image context
- **WHEN** the agent sends a screenshot
- **THEN** it is included as vision input

#### Scenario: Backend returns tool calls
- **WHEN** the backend responds with tool calls
- **THEN** the agent dispatches them via WebSocket

#### Scenario: Backend returns text only
- **WHEN** the backend responds with text only
- **THEN** the agent treats it as the final answer

#### Scenario: Backend connection failure
- **WHEN** the API is unreachable
- **THEN** the agent retries once after 5 seconds, then reports failure

### Requirement: MCP Server in Termux Core

The MCP server SHALL run in Layer B and expose Android-native tools.

#### Scenario: MCP server starts with Termux core
- **WHEN** the Termux core starts
- **THEN** the MCP server is reachable within 5 seconds

#### Scenario: MCP server responds to tools/list
- **WHEN** a client sends tools/list
- **THEN** the server returns the full schema

#### Scenario: MCP server responds to tools/call
- **WHEN** a client sends tools/call
- **THEN** the server routes to the correct implementation

#### Scenario: MCP server handles malformed input
- **WHEN** the server receives malformed JSON
- **THEN** it returns an error and does not crash

### Requirement: Termux-Specific Tool: termux_exec

The `termux_exec` tool SHALL provide scoped shell access.

#### Scenario: Execute shell command
- **WHEN** the agent sends termux_exec
- **THEN** the command runs in Termux and returns stdout, stderr, return code

#### Scenario: termux_exec is scoped
- **WHEN** the agent sends termux_exec
- **THEN** the working directory is restricted to Termux $HOME by default

#### Scenario: termux_exec timeout
- **WHEN** a command exceeds the timeout (default: 30s)
- **THEN** it is killed and a timeout error is returned
