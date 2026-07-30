"""WebSocket server for Layer B (Termux core).

Listens on 127.0.0.1 for connections from Layer A (native Android app).
Handles command/result/event protocol with request-id correlation.
"""

import asyncio
import json
import logging
import uuid
from typing import Any

logger = logging.getLogger(__name__)


class WebSocketServer:
    """WebSocket server that bridges Layer A and Layer B.

    - Accepts a single persistent connection from Layer A
    - Routes commands to the tool dispatcher
    - Sends results back with request-id correlation
    - Receives unsolicited events (consent revoked, app killed, etc.)
    """

    # Read-only commands that are safe to re-issue on reconnect
    READ_ONLY_COMMANDS = {"screen_read", "screenshot", "ocr", "read_screen_text"}

    def __init__(self, host: str = "127.0.0.1", port: int = 12345):
        self.host = host
        self.port = port
        self._clients: set = set()
        self._pending_results: dict[str, dict] = {}
        self._command_handler = None
        self._event_handler = None
        self._is_stopped = False

    def set_command_handler(self, handler) -> None:
        """Set the function that processes commands from Layer A."""
        self._command_handler = handler

    def set_event_handler(self, handler) -> None:
        """Set the function that processes events from Layer A."""
        self._event_handler = handler

    async def start(self) -> None:
        """Start the WebSocket server."""
        import websockets

        logger.info(f"WebSocket server starting on ws://{self.host}:{self.port}")
        async with websockets.serve(self._handle_connection, self.host, self.port):
            await asyncio.Future()  # Run forever

    async def _handle_connection(self, websocket) -> None:
        """Handle a new WebSocket connection from Layer A."""
        self._clients.add(websocket)
        logger.info(f"Layer A connected. Total clients: {len(self._clients)}")

        try:
            async for message in websocket:
                await self._handle_message(websocket, message)
        except Exception as e:
            logger.error(f"Connection error: {e}")
        finally:
            self._clients.discard(websocket)
            logger.info("Layer A disconnected")

    async def _handle_message(self, websocket, message: str) -> None:
        """Route an incoming message."""
        try:
            data = json.loads(message)
        except json.JSONDecodeError:
            logger.warning("Received malformed JSON")
            return

        msg_type = data.get("type")

        if msg_type == "result":
            await self._handle_result(data)
        elif msg_type == "event":
            await self._handle_event(data)
        else:
            logger.warning(f"Unknown message type: {msg_type}")

    async def _handle_result(self, data: dict) -> None:
        """Handle a result from Layer A (response to a command)."""
        request_id = data.get("request_id")
        if not request_id:
            logger.warning("Result missing request_id")
            return

        # Store the result for the waiting command
        self._pending_results[request_id] = data
        logger.debug(f"Result received for {request_id}")

    async def _handle_event(self, data: dict) -> None:
        """Handle an unsolicited event from Layer A."""
        event_type = data.get("event_type")
        event_data = data.get("data", {})
        logger.info(f"Event: {event_type}")

        if self._event_handler:
            self._event_handler(event_type, event_data)

    # ── Public API ───────────────────────────────────────────────────────

    async def send_command(
        self,
        action: str,
        params: dict | None = None,
    ) -> dict:
        """Send a command to Layer A and wait for the result.

        Returns the result dict. Raises TimeoutError if no response within 30s.
        """
        if self._is_stopped:
            return {"request_id": "", "status": "stopped", "error": "Agent is stopped"}

        if not self._clients:
            return {"request_id": "", "status": "error", "error": "No client connected"}

        request_id = str(uuid.uuid4())
        message = json.dumps({
            "type": "command",
            "request_id": request_id,
            "action": action,
            "params": params or {},
        })

        # Send to the first (should be only) client
        client = next(iter(self._clients))
        await client.send(message)

        # Wait for result with timeout
        for _ in range(300):  # 30 seconds at 100ms intervals
            if request_id in self._pending_results:
                result = self._pending_results.pop(request_id)
                return result
            await asyncio.sleep(0.1)

        return {"request_id": request_id, "status": "error", "error": "Timeout waiting for result"}

    async def broadcast_event(self, event_type: str, data: dict | None = None) -> None:
        """Send an event to all connected clients."""
        if not self._clients:
            return

        message = json.dumps({
            "type": "event",
            "event_type": event_type,
            "data": data or {},
        })

        for client in self._clients:
            try:
                await client.send(message)
            except Exception as e:
                logger.error(f"Failed to send event to client: {e}")

    def mark_stopped(self) -> None:
        """Mark the server as stopped. All commands return 'stopped' status."""
        self._is_stopped = True
        self._pending_results.clear()

    def reset_stopped(self) -> None:
        """Reset the stopped state."""
        self._is_stopped = False

    @property
    def is_connected(self) -> bool:
        """Check if any client is connected."""
        return len(self._clients) > 0
