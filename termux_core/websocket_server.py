"""WebSocket server for Layer B (Termux core).

Listens on 127.0.0.1 for connections from Layer A (native Android app).
Handles command/result/event protocol with request-id correlation.

Safety: Requires Bearer token authentication on connection. Token is
generated on server start and must be provided by the client.
"""

import asyncio
import json
import logging
import secrets
import uuid
from typing import Any

logger = logging.getLogger(__name__)


class WebSocketServer:
    """WebSocket server that bridges Layer A and Layer B.

    Layer B = server (listens)
    Layer A = client (connects)

    Commands flow A→B (tap, screen_read).
    Results flow B→A (response to commands).
    Events flow A→B (screen_changed, app_opened).
    """

    # Read-only commands that are safe to re-issue on reconnect
    READ_ONLY_COMMANDS = {"screen_read", "screenshot", "ocr", "read_screen_text"}

    def __init__(self, host: str = "127.0.0.1", port: int = 12345, auth_token: str | None = None):
        """Initialize WebSocket server.

        Args:
            host: Host to bind to (default: 127.0.0.1).
            port: Port to listen on (default: 12345).
            auth_token: Authentication token. If None, a random token is generated.
        """
        self.host = host
        self.port = port
        self._clients: set = set()
        self._pending_results: dict[str, dict] = {}
        self._command_handler = None
        self._event_handler = None
        self._is_stopped = False
        # Generate auth token if not provided
        self._auth_token = auth_token or secrets.token_urlsafe(32)
        logger.info(f"WebSocket server initialized with auth token (first 8 chars: {self._auth_token[:8]}...)")

    @property
    def auth_token(self) -> str:
        """Get the authentication token."""
        return self._auth_token

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
        async with websockets.serve(
            self._handle_connection,
            self.host,
            self.port,
            process_request=self._validate_auth,
        ):
            await asyncio.Future()  # Run forever

    async def _validate_auth(self, path, request_headers) -> None:
        """Validate authentication token from client.

        Args:
            path: Request path.
            request_headers: HTTP headers from client.

        Returns:
            None if auth is valid, or an HTTP error response tuple.
        """
        auth_header = request_headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            logger.warning("WebSocket connection rejected: missing Authorization header")
            return (401, [("WWW-Authenticate", "Bearer")], b"Unauthorized: missing token")

        token = auth_header[7:]  # Strip "Bearer "
        if not secrets.compare_digest(token, self._auth_token):
            logger.warning("WebSocket connection rejected: invalid token")
            return (403, [], b"Forbidden: invalid token")

        logger.info("WebSocket client authenticated successfully")
        return None

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
        if not request_id or request_id not in self._pending_results:
            logger.warning(f"Received result for unknown request: {request_id}")
            return

        result_data = data.get("data", {})
        self._pending_results[request_id] = {
            "status": "completed",
            "data": result_data,
        }
        logger.debug(f"Result received for {request_id}")

    async def _handle_event(self, data: dict) -> None:
        """Handle an unsolicited event from Layer A."""
        event_type = data.get("event_type")
        event_data = data.get("data", {})

        if not event_type:
            logger.warning("Received event without event_type")
            return

        logger.debug(f"Event received: {event_type}")

        if self._event_handler:
            self._event_handler(event_type, event_data)

    # ── Public API ───────────────────────────────────────────────────────

    async def send_command(
        self,
        action: str,
        params: dict | None = None,
        timeout: float = 30.0,
    ) -> dict:
        """Send a command to Layer A and wait for the result.

        Args:
            action: Command name (e.g. "tap", "screen_read").
            params: Command parameters.
            timeout: Seconds to wait for result.

        Returns:
            Result data from Layer A.
        """
        if self._is_stopped:
            return {"request_id": None, "status": "stopped", "data": None}

        if not self._clients:
            return {"request_id": None, "status": "error", "error": "No clients connected"}

        request_id = str(uuid.uuid4())
        message = {
            "type": "command",
            "request_id": request_id,
            "action": action,
            "params": params or {},
        }

        # Register pending result
        self._pending_results[request_id] = {"status": "pending"}

        # Broadcast to all clients
        for client in self._clients:
            try:
                await client.send(json.dumps(message))
            except Exception as e:
                logger.error(f"Failed to send command to client: {e}")

        # Wait for result
        try:
            async with asyncio.timeout(timeout):
                while self._pending_results.get(request_id, {}).get("status") == "pending":
                    await asyncio.sleep(0.05)

            result = self._pending_results.pop(request_id, {})
            return {
                "request_id": request_id,
                "status": result.get("status", "error"),
                "data": result.get("data"),
            }
        except asyncio.TimeoutError:
            self._pending_results.pop(request_id, None)
            return {"request_id": request_id, "status": "error", "error": "Timeout waiting for result"}

    async def broadcast_event(self, event_type: str, data: dict | None = None) -> None:
        """Send an event to all connected clients."""
        if not self._clients:
            return

        message = {
            "type": "event",
            "event_type": event_type,
            "data": data or {},
        }

        for client in self._clients:
            try:
                await client.send(json.dumps(message))
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
