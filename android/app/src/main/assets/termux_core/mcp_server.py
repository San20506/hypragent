"""HYPR Agent MCP Server for Android (Termux core — Layer B).

Runs the WebSocket server, Hermes Agent loop, and audit logger.
Entry point for the Termux core process.

Run as: python3 -m termux_core.mcp_server [--config path] [--port N]
"""

import argparse
import asyncio
import json
import logging
import os

try:
    import yaml
except ImportError:
    yaml = None  # ponytail: YAML optional, defaults + JSON config still work

from .agent_loop import HermesAgentLoop
from .audit_logger import AuditLogger
from .backends.base import BackendAdapter
from .websocket_server import WebSocketServer

logging.basicConfig(
    level=logging.INFO,
    format="[%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)


def _load_config() -> dict:
    """Load configuration from standard locations."""
    paths = [
        os.path.expanduser("~/.hypragent/config.yaml"),
        os.path.join(os.path.dirname(__file__), "..", "config.yaml"),
    ]
    for path in paths:
        if os.path.isfile(path):
            with open(path) as f:
                if yaml is not None:
                    return yaml.safe_load(f) or {}
                return json.load(f)  # ponytail: JSON fallback if no PyYAML

    # Defaults
    return {
        "backend": {
            "active": "claude",
            "claude": {"model": "claude-sonnet-4-5", "api_key_env": "ANTHROPIC_API_KEY"},
            "gemini": {"model": "gemini-2.5-flash", "api_key_env": "GEMINI_API_KEY"},
            "ollama": {"endpoint": "http://localhost:11434", "model": "llava"},
        },
        "loop": {"max_steps": 20, "confirm_destructive_actions": True},
        "websocket": {"port": 12345},
    }


def _create_backend(config: dict) -> BackendAdapter:
    """Create the AI backend adapter from config.

    Backend SDKs are imported lazily so only the active backend's
    SDK needs to be installed.
    """
    backend_config = config.get("backend", {})
    active = backend_config.get("active", "claude")

    if active == "claude":
        from .backends.claude import ClaudeBackend

        c = backend_config.get("claude", {})
        return ClaudeBackend(
            model=c.get("model", "claude-sonnet-4-5"),
            api_key=os.environ.get(c.get("api_key_env", "ANTHROPIC_API_KEY"), ""),
        )
    elif active == "gemini":
        from .backends.gemini import GeminiBackend

        c = backend_config.get("gemini", {})
        return GeminiBackend(
            model=c.get("model", "gemini-2.5-flash"),
            api_key=os.environ.get(c.get("api_key_env", "GEMINI_API_KEY"), ""),
        )
    elif active == "ollama":
        from .backends.ollama import OllamaBackend

        c = backend_config.get("ollama", {})
        return OllamaBackend(
            endpoint=c.get("endpoint", "http://localhost:11434"),
            model=c.get("model", "llava"),
        )
    else:
        raise ValueError(f"Unknown backend: {active}")


async def run(config: dict) -> None:
    """Main entry point."""
    port = config.get("websocket", {}).get("port", 12345)

    # Initialize components
    audit_logger = AuditLogger()
    await audit_logger.start()

    ws_server = WebSocketServer(port=port)
    backend = _create_backend(config)
    agent = HermesAgentLoop(config, backend, ws_server, audit_logger)

    # Track the running agent task so stop/revoke can interrupt it
    agent_task: asyncio.Task | None = None

    def handle_event(event_type: str, data: dict) -> None:
        nonlocal agent_task
        logger.info(f"Event received: {event_type}")
        audit_logger.log_event(event_type, "layer_a", data)

        if event_type == "task_submitted":
            task_text = data.get("task", "")
            if task_text and (agent_task is None or agent_task.done()):
                agent_task = asyncio.create_task(agent.run(task_text))
                asyncio.get_event_loop().call_soon(
                    lambda: asyncio.create_task(
                        ws_server.broadcast_event("task_started", {"task": task_text})
                    )
                )
            elif agent_task is not None and not agent_task.done():
                logger.warning("Task already running, ignoring submission")
        elif event_type == "consent_revoked":
            agent.revoke_consent()
        elif event_type == "emergency_stop":
            agent.stop()
        elif event_type == "agent_reset":
            ws_server.reset_stopped()

    ws_server.set_event_handler(handle_event)

    logger.info(f"HYPR Agent Termux core starting on port {port}")
    logger.info(f"Backend: {config.get('backend', {}).get('active', 'unknown')}")

    try:
        await ws_server.start()
    finally:
        if agent_task is not None and not agent_task.done():
            agent.stop()
            agent_task.cancel()
        await audit_logger.stop()


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="hypragent-termux",
        description="HYPR Agent Termux Core — Android MCP server (Layer B)",
    )
    parser.add_argument("--config", help="Path to config.yaml")
    parser.add_argument("--port", type=int, default=12345, help="WebSocket port")
    args = parser.parse_args()

    config = _load_config()
    if args.config:
        with open(args.config) as f:
            if yaml is not None:
                config.update(yaml.safe_load(f) or {})
            else:
                config.update(json.load(f))
    if args.port:
        config.setdefault("websocket", {})["port"] = args.port

    asyncio.run(run(config))


if __name__ == "__main__":
    main()
