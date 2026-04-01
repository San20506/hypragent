"""Agent loop — perceive → reason → act cycle. Implemented in Milestone M6."""

from agent.backends.base import AgentResponse, BackendAdapter


class AgentLoop:
    """Autonomous agent execution loop.

    State machine:
        IDLE → PERCEIVE → REASON → ACT → CHECK_TERMINATION → PERCEIVE (repeat)

    Termination conditions:
        - task_complete: backend signals stop_reason == "end_turn" with no tool calls
        - max_steps_reached: step count >= config loop.max_steps
        - kill_switch_triggered: user presses kill_switch_key combination
    """

    def __init__(self, config: dict, backend: BackendAdapter) -> None:
        self.config = config
        self.backend = backend
        self._step = 0
        self._history: list[dict] = []
        # TODO M10: Initialize kill switch listener

    def run(self, task: str) -> None:
        """Run the agent loop until termination condition met.

        Args:
            task: Natural language description of the task to complete.
        """
        # TODO M6: Implement main loop
        raise NotImplementedError("M6: AgentLoop.run not yet implemented")

    def _perceive(self) -> dict:
        """Capture screenshot and OCR text from current screen state.

        Returns:
            Perception dict with keys: screenshot_b64, ocr_text.
        """
        # TODO M6: Call tools.screenshot + tools.ocr
        raise NotImplementedError("M6: AgentLoop._perceive not yet implemented")

    def _reason(self, perception: dict, task: str) -> AgentResponse:
        """Send perception + history to backend for reasoning.

        Returns:
            AgentResponse with content and any tool_calls.
        """
        # TODO M6: Build message list and call backend.send_message
        raise NotImplementedError("M6: AgentLoop._reason not yet implemented")

    def _act(self, response: AgentResponse) -> list[dict]:
        """Execute tool calls from backend response.

        Returns:
            List of tool result dicts to append to history.
        """
        # TODO M6: Dispatch to tool registry, handle confirm_destructive_actions
        raise NotImplementedError("M6: AgentLoop._act not yet implemented")

    def _check_termination(self, response: AgentResponse) -> bool:
        """Return True if loop should stop.

        Checks: stop_reason, max_steps, kill_switch state.
        """
        # TODO M6: Implement termination logic
        raise NotImplementedError("M6: AgentLoop._check_termination not yet implemented")
