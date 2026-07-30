"""Agent loop — perceive → reason → act cycle. Milestones M6 + M10."""

import json
import os
import signal
from datetime import datetime, timezone

from tools.screenshot import capture_fullscreen
from tools.ocr import extract_text_fullscreen
from tools.dispatch import dispatch_tool
from agent.backends.base import AgentResponse, BackendAdapter
from agent.action_executor import execute_plan


_SYSTEM_PROMPT = (
    "You are a desktop automation agent running on Hyprland/Wayland. "
    "You control the desktop by calling tools. You receive screenshots and OCR text "
    "to perceive the current screen state. "
    "Complete the given task by using tools, then respond with 'TASK COMPLETE' "
    "when finished and make no more tool calls. "
    "For multi-step sequences, prefer execute_plan with a dependency graph. "
    "Independent actions (read queries, app launches) should have empty depends_on "
    "to run in parallel. Input actions (mouse, keyboard) and perception "
    "(screenshot, OCR) should depend on the actions that set up their context. "
    "For single-step actions, use individual tools as before."
)

_AUDIT_LOG = os.path.expanduser("~/.config/hypr-agent/audit.log")

_DESTRUCTIVE_TOOLS = {"file_write", "file_move", "file_delete", "terminal_run"}

AGENT_TOOLS = [
    {"name": "take_screenshot", "description": "Capture the current screen",
     "inputSchema": {"type": "object", "properties": {}}},
    {"name": "mouse_move", "description": "Move mouse cursor to absolute screen coordinates",
     "inputSchema": {"type": "object", "properties": {
         "x": {"type": "integer"}, "y": {"type": "integer"}},
         "required": ["x", "y"]}},
    {"name": "mouse_click", "description": "Move to coordinates and click",
     "inputSchema": {"type": "object", "properties": {
         "x": {"type": "integer"}, "y": {"type": "integer"},
         "button": {"type": "string", "enum": ["left", "right", "middle"]}},
         "required": ["x", "y"]}},
    {"name": "mouse_drag", "description": "Click and drag from one position to another",
     "inputSchema": {"type": "object", "properties": {
         "from_x": {"type": "integer"}, "from_y": {"type": "integer"},
         "to_x": {"type": "integer"}, "to_y": {"type": "integer"}},
         "required": ["from_x", "from_y", "to_x", "to_y"]}},
    {"name": "mouse_scroll", "description": "Scroll at screen coordinates",
     "inputSchema": {"type": "object", "properties": {
         "x": {"type": "integer"}, "y": {"type": "integer"},
         "direction": {"type": "string", "enum": ["up", "down"]},
         "amount": {"type": "integer"}},
         "required": ["x", "y", "direction"]}},
    {"name": "keyboard_type", "description": "Type a string of text",
     "inputSchema": {"type": "object", "properties": {
         "text": {"type": "string"}}, "required": ["text"]}},
    {"name": "keyboard_press", "description": "Press a key or key combination (e.g. Return, ctrl+c)",
     "inputSchema": {"type": "object", "properties": {
         "key": {"type": "string"}}, "required": ["key"]}},
    {"name": "read_screen_text", "description": "Extract all visible text from screen via OCR",
     "inputSchema": {"type": "object", "properties": {}}},
    {"name": "terminal_run", "description": "Run a shell command and return output",
     "inputSchema": {"type": "object", "properties": {
         "command": {"type": "string"},
         "cwd": {"type": "string"},
         "timeout": {"type": "integer"}},
         "required": ["command"]}},
    {"name": "file_read", "description": "Read a text file",
     "inputSchema": {"type": "object", "properties": {
         "path": {"type": "string"}}, "required": ["path"]}},
    {"name": "file_write", "description": "Write content to a file",
     "inputSchema": {"type": "object", "properties": {
         "path": {"type": "string"}, "content": {"type": "string"}},
         "required": ["path", "content"]}},
    {"name": "browser_open", "description": "Open a URL in the browser",
     "inputSchema": {"type": "object", "properties": {
         "url": {"type": "string"}}, "required": ["url"]}},
    {"name": "browser_get_text", "description": "Get visible text from a browser element",
     "inputSchema": {"type": "object", "properties": {
         "selector": {"type": "string"}}, "required": ["selector"]}},
    # ── Hyprland compositor tools (M2.5) ──────────────────────────────────────
    {"name": "hyprland_workspace_list",
     "description": "List all Hyprland workspaces — id, name, window count, monitor, active flag",
     "inputSchema": {"type": "object", "properties": {}}},
    {"name": "hyprland_workspace_switch",
     "description": "Switch to workspace by id, name, +1, -1, or 'previous'",
     "inputSchema": {"type": "object", "properties": {
         "target": {"type": "string"}}, "required": ["target"]}},
    {"name": "hyprland_clients",
     "description": "List all open windows — class, title, pid, workspace, position, size",
     "inputSchema": {"type": "object", "properties": {}}},
    {"name": "hyprland_active_window",
     "description": "Get the focused window — class, title, workspace (pre-action sanity check)",
     "inputSchema": {"type": "object", "properties": {}}},
    {"name": "hyprland_focus_window",
     "description": "Focus window by class:name or address:0x...",
     "inputSchema": {"type": "object", "properties": {
         "target": {"type": "string"}}, "required": ["target"]}},
    # ── Parallel execution tool ──────────────────────────────────────────────
    {"name": "execute_plan",
     "description": "Execute a batch of actions with dependency-aware parallelism. "
                    "Independent actions run in parallel. Actions with dependencies wait "
                    "for their predecessors. Returns results from all actions plus a "
                    "verification screenshot and OCR snapshot. "
                    "Use this for multi-step sequences instead of individual tool calls.",
     "inputSchema": {"type": "object", "properties": {
         "actions": {"type": "array", "items": {
             "type": "object", "properties": {
                 "id": {"type": "string"},
                 "tool": {"type": "string"},
                 "args": {"type": "object"},
                 "depends_on": {"type": "array", "items": {"type": "string"}},
             }, "required": ["id", "tool", "args"]}},
     }, "required": ["actions"]}},
]


def _audit(tool_name: str, arguments: dict, result: str) -> None:
    """Append a JSON line to the audit log."""
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "tool": tool_name,
        "args": arguments,
        "result": result[:200],
    }
    with open(_AUDIT_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def _confirm(tool_name: str, arguments: dict, config: dict) -> bool:
    """Prompt user to confirm a destructive action. Returns True to proceed."""
    if not config.get("loop", {}).get("confirm_destructive_actions", True):
        return True
    prompt = f"[hypr-agent] Allow {tool_name}({arguments})? [y/N] "
    try:
        answer = input(prompt).strip().lower()
        return answer in ("y", "yes")
    except (EOFError, KeyboardInterrupt):
        return False


def _dispatch_tool(name: str, arguments: dict, config: dict | None = None) -> str:
    """Dispatch a tool call by name and return the result as a string."""
    if config is not None and name in _DESTRUCTIVE_TOOLS:
        if not _confirm(name, arguments, config):
            return "Cancelled by user"
    if name == "execute_plan":
        actions = arguments["actions"]
        def _plan_dispatch(tool: str, args: dict) -> str:
            return _dispatch_tool(tool, args, config)
        result = execute_plan(actions, _plan_dispatch, verify=True)
        return json.dumps(result, indent=2)
    return dispatch_tool(name, arguments)


class AgentLoop:
    """Autonomous agent execution loop.

    State machine:
        IDLE → PERCEIVE → REASON → ACT → CHECK_TERMINATION → PERCEIVE (repeat)

    Termination conditions:
        - task_complete: backend signals stop_reason == "end_turn" with no tool calls
        - max_steps_reached: step count >= config loop.max_steps
        - kill_switch_triggered: SIGINT received (Ctrl+C)
    """

    def __init__(self, config: dict, backend: BackendAdapter) -> None:
        self.config = config
        self.backend = backend
        self._step = 0
        self._history: list[dict] = []
        self._killed = False
        os.makedirs(os.path.dirname(_AUDIT_LOG), exist_ok=True)
        signal.signal(signal.SIGINT, self._handle_sigint)

    def _handle_sigint(self, signum: int, frame: object) -> None:
        self._killed = True

    def run(self, task: str) -> None:
        """Run the agent loop until termination condition met.

        Args:
            task: Natural language description of the task to complete.
        """
        self._step = 0
        self._history = []
        self._killed = False

        while True:
            perception = self._perceive()
            response = self._reason(perception, task)

            if self._check_termination(response):
                break

            tool_results = self._act(response)

            # Append assistant turn with tool_use blocks if any
            if response.tool_calls:
                assistant_content: list[dict] | str = []
                if response.content:
                    assistant_content.append({"type": "text", "text": response.content})
                for tc in response.tool_calls:
                    assistant_content.append({
                        "type": "tool_use",
                        "id": tc["id"],
                        "name": tc["name"],
                        "input": tc["input"],
                    })
            else:
                assistant_content = response.content

            self._history.append({"role": "assistant", "content": assistant_content})

            if tool_results:
                self._history.append({"role": "user", "content": tool_results})

            self._step += 1

    def _perceive(self) -> dict:
        """Capture screenshot and OCR text from current screen state.

        Returns:
            Perception dict with keys: screenshot_b64, ocr_text.
        """
        return {
            "screenshot_b64": capture_fullscreen(),
            "ocr_text": extract_text_fullscreen(),
        }

    def _reason(self, perception: dict, task: str) -> AgentResponse:
        """Send perception + history to backend for reasoning.

        Returns:
            AgentResponse with content and any tool_calls.
        """
        ocr_text = perception["ocr_text"].strip()
        if not self._history:
            content = f"{_SYSTEM_PROMPT}\n\nTask: {task}\n\nScreen OCR:\n{ocr_text}"
        else:
            content = f"Screen OCR:\n{ocr_text}"

        messages = [*self._history, {"role": "user", "content": content}]

        return self.backend.send_message(
            messages=messages,
            tools=AGENT_TOOLS,
            images=[perception["screenshot_b64"]],
        )

    def _act(self, response: AgentResponse) -> list[dict]:
        """Execute tool calls from backend response.

        Returns:
            List of tool result dicts in Claude tool_result format.
        """
        results = []
        for tc in response.tool_calls:
            result_str = _dispatch_tool(tc["name"], tc["input"], self.config)
            _audit(tc["name"], tc["input"], result_str)
            results.append({
                "type": "tool_result",
                "tool_use_id": tc["id"],
                "content": result_str,
            })
        return results

    def _check_termination(self, response: AgentResponse) -> bool:
        """Return True if loop should stop.

        Terminates when:
          - Kill switch triggered (SIGINT)
          - Max steps reached
          - Model has no more tool calls (regardless of stop_reason)
          - Model hit token limit (max_tokens/length) — avoid infinite retry loop

        The old behaviour only checked stop_reason == "end_turn", which meant
        a model hitting max_tokens with no tool calls would loop forever
        re-sending the same screenshot + OCR text until max_steps exhausted.
        """
        if self._killed:
            return True
        max_steps = self.config.get("loop", {}).get("max_steps", 20)
        if self._step >= max_steps:
            return True
        # If the model made no tool calls, there's nothing to execute.
        # Stop regardless of whether it said "end_turn", "stop", "max_tokens",
        # or anything else — the cycle is complete.
        if not response.tool_calls:
            return True
        # Model requested tools but hit a token limit mid-reasoning.
        # Continuing would feed the same context and hit the same limit.
        if response.stop_reason in ("max_tokens", "length"):
            return True
        return False
