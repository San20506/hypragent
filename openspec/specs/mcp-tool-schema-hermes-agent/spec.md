## Purpose

Layer B components: the Android-native MCP tool schema (versioned independently), the Hermes Agent reasoning loop (perceive-reason-act cycle), the AI Backend Adapter (Claude/Gemini/Ollama, swappable via config), the MCP server in Termux core, and the scoped `termux_exec` shell tool.

## Requirements

### Requirement: Android-Native MCP Tool Schema

The MCP tool schema SHALL define the Android-native tools that the Hermes Agent can call. The schema is versioned independently from the Hermes Agent reasoning loop.

#### Scenario: Tool schema versioned independently
- **WHEN** the MCP tool schema is updated (new tools added, parameters changed)
- **THEN** the Hermes Agent reasoning loop continues to work with the old schema until it is restarted

#### Scenario: Tool schema includes screen_read
- **WHEN** the MCP server starts
- **THEN** the tool schema includes `screen_read` with input parameters for region (optional) and output format (node tree or screenshot)

#### Scenario: Tool schema includes gesture tools
- **WHEN** the MCP server starts
- **THEN** the tool schema includes `tap`, `swipe`, `long_press`, and `pinch` with coordinate parameters

#### Scenario: Tool schema includes OCR tool
- **WHEN** the MCP server starts
- **THEN** the tool schema includes `read_screen_text` with input parameters for region (optional)

#### Scenario: Tool schema includes file operations
- **WHEN** the MCP server starts
- **THEN** the tool schema includes `file_read`, `file_write`, `file_list`, `file_move`, `file_delete` with path and content parameters

#### Scenario: Tool schema includes terminal execution
- **WHEN** the MCP server starts
- **THEN** the tool schema includes `termux_exec` with command and timeout parameters

### Requirement: Hermes Agent Reasoning Loop

The Hermes Agent SHALL run in the Termux core (Layer B) and execute the perceive-reason-act cycle. It sends commands to Layer A via the WebSocket bridge and receives results.

#### Scenario: Full agent cycle
- **WHEN** the Hermes Agent receives a task
- **THEN** it executes the cycle: read screen -> reason (AI backend call) -> send command -> receive result -> repeat until task complete or max steps reached

#### Scenario: Agent uses screen_read for perception
- **WHEN** the Hermes Agent needs to see the current screen state
- **THEN** it sends a `screen_read` command via WebSocket and uses the returned node tree or screenshot for reasoning

#### Scenario: Agent uses gesture tools for action
- **WHEN** the Hermes Agent decides to tap, swipe, or long-press
- **THEN** it sends the corresponding gesture command via WebSocket and waits for the result

#### Scenario: Agent handles command failure
- **WHEN** a command returns a `status: "error"` result
- **THEN** the agent logs the error, incorporates it into its reasoning, and decides whether to retry, try an alternative, or report failure

#### Scenario: Agent respects max steps
- **WHEN** the agent reaches the configured maximum step count (default: 20)
- **THEN** it stops the current task and reports "max steps reached" to the caller

#### Scenario: Agent responds to consent_revoked event
- **WHEN** the agent receives a "consent_revoked" event from Layer A
- **THEN** it immediately stops the current task, discards pending commands, and reports "consent revoked" to the caller

### Requirement: AI Backend Adapter

The AI backend adapter SHALL support Claude, Gemini, and Ollama, swappable via configuration. All three backends support vision (image input).

#### Scenario: Backend selected by configuration
- **WHEN** the configuration specifies `backend.active: claude`
- **THEN** the Hermes Agent uses the Claude adapter for all reasoning calls

#### Scenario: Backend swap without code change
- **WHEN** the configuration is changed from `backend.active: claude` to `backend.active: gemini`
- **THEN** the Hermes Agent uses the Gemini adapter after restart without any code changes

#### Scenario: Backend sends image context
- **WHEN** the Hermes Agent sends a screenshot to the AI backend
- **THEN** the screenshot is included as a vision (image) input alongside the text prompt and tool definitions

#### Scenario: Backend returns tool calls
- **WHEN** the AI backend responds with tool calls
- **THEN** the Hermes Agent parses the tool calls and dispatches them to the WebSocket bridge

#### Scenario: Backend returns text only
- **WHEN** the AI backend responds with text but no tool calls
- **THEN** the Hermes Agent treats the text as the final answer and completes the task

#### Scenario: Backend connection failure
- **WHEN** the AI backend API is unreachable or returns an error
- **THEN** the Hermes Agent retries once after 5 seconds, then reports the failure to the caller

### Requirement: MCP Server in Termux Core

The MCP server SHALL run in the Termux core (Layer B) and expose the Android-native tools.

#### Scenario: MCP server starts with Termux core
- **WHEN** the Termux core process starts
- **THEN** the MCP server initializes and becomes reachable via local WebSocket within 5 seconds

#### Scenario: MCP server responds to tools/list
- **WHEN** a client sends `tools/list` to the MCP server
- **THEN** the server returns the full Android-native tool schema with JSON Schema definitions for all tools

#### Scenario: MCP server responds to tools/call
- **WHEN** a client sends `tools/call` with a tool name and arguments
- **THEN** the server routes to the correct tool implementation and returns the result

#### Scenario: MCP server handles malformed input
- **WHEN** the MCP server receives malformed JSON or an unknown tool name
- **THEN** it returns a structured error response and does not crash

### Requirement: Termux-Specific Tool: termux_exec

The `termux_exec` tool SHALL provide scoped shell access within the Termux environment.

#### Scenario: Execute shell command in Termux
- **WHEN** the agent sends a `termux_exec` command with a shell command
- **THEN** the command executes in the Termux shell environment and returns stdout, stderr, and return code

#### Scenario: termux_exec is scoped
- **WHEN** the agent sends a `termux_exec` command
- **THEN** the command runs within the Termux sandbox with the working directory restricted to the Termux home directory (`$HOME`) by default, and cannot access files outside the allowed scope unless explicitly configured

#### Scenario: termux_exec timeout
- **WHEN** a `termux_exec` command runs longer than the configured timeout (default: 30 seconds)
- **THEN** the command is killed and a timeout error is returned
