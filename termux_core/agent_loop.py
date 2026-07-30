"""Hermes Agent reasoning loop for Android (Layer B).

Perceive → Reason → Act cycle, adapted from the desktop version.
Sends commands to Layer A via WebSocket, receives results.
"""

import asyncio
import json
import logging
from typing import Any

from .audit_logger import AuditLogger
from .websocket_server import WebSocketServer

logger = logging.getLogger(__name__)


_SYSTEM_PROMPT = (
    "You are an Android automation agent running in a Termux environment. "
    "You control an Android device by calling tools that are executed by the "
    "native Android app (Layer A) via WebSocket. "
    "You receive UI tree data or OCR text to perceive the current screen state. "
    "Complete the given task by using tools, then respond with 'TASK COMPLETE' "
    "when finished and make no more tool calls."
)


class HermesAgentLoop:
    """Autonomous agent execution loop for Android.

    State machine:
        IDLE → PERCEIVE → REASON → ACT → CHECK_TERMINATION → PERCEIVE (repeat)

    Termination conditions:
        - task_complete: no more tool calls
        - max_steps_reached: step count >= max_steps
        - consent_revoked: user revoked consent
        - emergency_stop: emergency stop triggered
    """

    def __init__(
        self,
        config: dict,
        backend,  # BackendAdapter instance
        ws_server: WebSocketServer,
        audit_logger: AuditLogger,
    ) -> None:
        self.config = config
        self.backend = backend
        self.ws = ws_server
        self.audit = audit_logger
        self._step = 0
        self._history: list[dict] = []
        self._killed = False
        self._consent_revoked = False
        self._max_steps = config.get("loop", {}).get("max_steps", 20)

    async def run(self, task: str) -> None:
        """Run the agent loop until termination condition met."""
        self._step = 0
        self._history = []
        self._killed = False
        self._consent_revoked = False

        logger.info(f"Agent starting task: {task}")

        try:
            while True:
                perception = await self._perceive()
                if perception.get("stopped"):
                    break

                response = await self._reason(perception, task)

                if self._check_termination(response):
                    break

                await self._act(response)
                self._step += 1

            await self.ws.broadcast_event("task_completed", {"steps": self._step})
        except Exception as e:
            logger.error(f"Agent failed: {e}")
            self.audit.log_error("agent_loop", str(e), {"step": self._step})
            await self.ws.broadcast_event("task_failed", {"error": str(e)})

        logger.info(f"Agent finished after {self._step} steps")

    def stop(self) -> None:
        """Trigger emergency stop."""
        self._killed = True
        self.audit.log_emergency_stop({"step": self._step})

    def revoke_consent(self) -> None:
        """Handle consent revocation."""
        self._consent_revoked = True

    async def _perceive(self) -> dict:
        """Get current screen state from Layer A."""
        if not self.ws.is_connected:
            return {"stopped": True, "error": "Layer A not connected"}

        result = await self.ws.send_command("screen_read")
        if result.get("status") == "stopped":
            return {"stopped": True}

        return {
            "screen_data": result.get("result", {}),
            "stopped": False,
        }

    async def _reason(self, perception: dict, task: str) -> dict:
        """Send perception to AI backend for reasoning."""
        screen_data = perception.get("screen_data", {})
        screen_text = json.dumps(screen_data, indent=2)

        if not self._history:
            content = f"{_SYSTEM_PROMPT}\n\nTask: {task}\n\nScreen state:\n{screen_text}"
        else:
            content = f"Screen state:\n{screen_text}"

        messages = [*self._history, {"role": "user", "content": content}]

        # Call the backend (async)
        response = await asyncio.to_thread(
            self.backend.send_message,
            messages=messages,
            tools=self._get_tool_schema(),
            images=[],  # Screenshots would come from Layer A
        )

        return {
            "content": response.content,
            "tool_calls": response.tool_calls,
            "stop_reason": response.stop_reason,
        }

    def _get_tool_schema(self) -> list[dict]:
        """Get the MCP tool schema for the backend."""
        from .android_tools import ANDROID_TOOLS
        return ANDROID_TOOLS

    async def _act(self, response: dict) -> list[dict]:
        """Execute tool calls from the backend response."""
        results = []
        for tc in response.get("tool_calls", []):
            tool_name = tc.get("name", "")
            tool_input = tc.get("input", {})

            # Status UI: tell Layer A which tool is running
            await self.ws.broadcast_event(
                "tool_call", {"tool": tool_name, "step": self._step + 1}
            )

            # Send command to Layer A via WebSocket
            result = await self.ws.send_command(tool_name, tool_input)
            result_str = json.dumps(result)

            # Audit log
            self.audit.log_command(
                request_id=result.get("request_id", ""),
                action=tool_name,
                params=tool_input,
                result=result,
            )

            results.append({
                "type": "tool_result",
                "tool_use_id": tc.get("id", ""),
                "content": result_str,
            })

            # Check if we should stop
            if result.get("status") == "stopped":
                self._killed = True
                break

        return results

    def _check_termination(self, response: dict) -> bool:
        """Return True if loop should stop."""
        if self._killed:
            return True
        if self._consent_revoked:
            return True
        if self._step >= self._max_steps:
            return True
        if not response.get("tool_calls"):
            return True
        if response.get("stop_reason") in ("max_tokens", "length"):
            return True
        return False
