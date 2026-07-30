"""Android-specific tools for the MCP server.

These tools are implemented by Layer A (native Android app) and
called by Layer B (Termux core) via the WebSocket bridge.
"""

import json
import logging
import subprocess
from typing import Any

logger = logging.getLogger(__name__)


# ── Tool definitions (MCP schema) ───────────────────────────────────────────

ANDROID_TOOLS = [
    {
        "name": "screen_read",
        "description": "Read the current screen UI tree. Returns node tree or OCR fallback.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "region": {
                    "type": "object",
                    "properties": {
                        "x": {"type": "integer"},
                        "y": {"type": "integer"},
                        "width": {"type": "integer"},
                        "height": {"type": "integer"},
                    },
                },
            },
        },
    },
    {
        "name": "tap",
        "description": "Tap at screen coordinates.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "x": {"type": "integer"},
                "y": {"type": "integer"},
            },
            "required": ["x", "y"],
        },
    },
    {
        "name": "swipe",
        "description": "Swipe from one point to another.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "x1": {"type": "integer"},
                "y1": {"type": "integer"},
                "x2": {"type": "integer"},
                "y2": {"type": "integer"},
                "duration_ms": {"type": "integer"},
            },
            "required": ["x1", "y1", "x2", "y2"],
        },
    },
    {
        "name": "long_press",
        "description": "Long-press at screen coordinates.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "x": {"type": "integer"},
                "y": {"type": "integer"},
                "hold_ms": {"type": "integer"},
            },
            "required": ["x", "y"],
        },
    },
    {
        "name": "pinch",
        "description": "Pinch gesture centered at coordinates.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "x": {"type": "integer"},
                "y": {"type": "integer"},
                "scale_factor": {"type": "number"},
            },
            "required": ["x", "y", "scale_factor"],
        },
    },
    {
        "name": "read_screen_text",
        "description": "Extract text from screen via OCR.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "region": {
                    "type": "object",
                    "properties": {
                        "x": {"type": "integer"},
                        "y": {"type": "integer"},
                        "width": {"type": "integer"},
                        "height": {"type": "integer"},
                    },
                },
            },
        },
    },
    {
        "name": "screenshot",
        "description": "Take a screenshot of the current screen.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "region": {
                    "type": "object",
                    "properties": {
                        "x": {"type": "integer"},
                        "y": {"type": "integer"},
                        "width": {"type": "integer"},
                        "height": {"type": "integer"},
                    },
                },
            },
        },
    },
    {
        "name": "file_read",
        "description": "Read a text file.",
        "inputSchema": {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
        },
    },
    {
        "name": "file_write",
        "description": "Write content to a file.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "content": {"type": "string"},
            },
            "required": ["path", "content"],
        },
    },
    {
        "name": "file_list",
        "description": "List directory contents.",
        "inputSchema": {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
        },
    },
    {
        "name": "file_move",
        "description": "Move or rename a file.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "src": {"type": "string"},
                "dst": {"type": "string"},
            },
            "required": ["src", "dst"],
        },
    },
    {
        "name": "file_delete",
        "description": "Delete a file.",
        "inputSchema": {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
        },
    },
    {
        "name": "termux_exec",
        "description": "Execute a shell command in the Termux environment.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "command": {"type": "string"},
                "timeout": {"type": "integer"},
            },
            "required": ["command"],
        },
    },
]


# ── Tool dispatch ───────────────────────────────────────────────────────────

# These tools are dispatched to Layer A via WebSocket
LAYER_A_TOOLS = {"screen_read", "tap", "swipe", "long_press", "pinch", "read_screen_text", "screenshot"}

# These tools run locally in Termux
LOCAL_TOOLS = {"file_read", "file_write", "file_list", "file_move", "file_delete", "termux_exec"}

# Read-only tools (safe to re-issue on reconnect)
READ_ONLY_TOOLS = {"screen_read", "read_screen_text", "screenshot", "file_read", "file_list"}


async def dispatch_android_tool(name: str, arguments: dict, ws_server=None) -> str:
    """Dispatch an Android tool call.

    Layer A tools are sent via WebSocket. Local tools run in Termux.
    Async because Layer A dispatch awaits the WebSocket round-trip —
    calling asyncio.run() here would crash inside the agent loop.
    """
    if name in LAYER_A_TOOLS:
        return await _dispatch_layer_a(name, arguments, ws_server)
    elif name in LOCAL_TOOLS:
        return _dispatch_local(name, arguments)
    else:
        return json.dumps({"error": f"Unknown tool: {name}"})


async def _dispatch_layer_a(name: str, arguments: dict, ws_server) -> str:
    """Send a tool call to Layer A via WebSocket."""
    if ws_server is None or not ws_server.is_connected:
        return json.dumps({"error": "Layer A not connected"})

    try:
        result = await ws_server.send_command(name, arguments)
        return json.dumps(result)
    except Exception as e:
        return json.dumps({"error": str(e)})


def _dispatch_local(name: str, arguments: dict) -> str:
    """Execute a local tool in the Termux environment."""
    try:
        if name == "termux_exec":
            return _termux_exec(arguments)
        elif name == "file_read":
            return _file_read(arguments)
        elif name == "file_write":
            return _file_write(arguments)
        elif name == "file_list":
            return _file_list(arguments)
        elif name == "file_move":
            return _file_move(arguments)
        elif name == "file_delete":
            return _file_delete(arguments)
        else:
            return json.dumps({"error": f"Unknown local tool: {name}"})
    except Exception as e:
        return json.dumps({"error": str(e)})


# ── Local tool implementations ──────────────────────────────────────────────

def _termux_exec(arguments: dict) -> str:
    """Execute a shell command in Termux, scoped to $HOME."""
    import os

    command = arguments["command"]
    timeout = arguments.get("timeout", 30)
    cwd = arguments.get("cwd", os.path.expanduser("~"))

    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd,
        )
        return json.dumps({
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
            "timed_out": False,
        })
    except subprocess.TimeoutExpired:
        return json.dumps({
            "stdout": "",
            "stderr": "",
            "returncode": -1,
            "timed_out": True,
        })


def _file_read(arguments: dict) -> str:
    """Read a text file."""
    path = arguments["path"]
    with open(path, encoding="utf-8") as f:
        return f.read()


def _file_write(arguments: dict) -> str:
    """Write content to a file."""
    path = arguments["path"]
    content = arguments["content"]
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return json.dumps({"status": "ok", "path": path})


def _file_list(arguments: dict) -> str:
    """List directory contents."""
    import os

    path = arguments["path"]
    entries = []
    for entry in os.listdir(path):
        full = os.path.join(path, entry)
        stat = os.stat(full)
        entries.append({
            "name": entry,
            "is_dir": os.path.isdir(full),
            "size": stat.st_size,
            "modified": stat.st_mtime,
        })
    return json.dumps(entries)


def _file_move(arguments: dict) -> str:
    """Move or rename a file."""
    import shutil

    src = arguments["src"]
    dst = arguments["dst"]
    shutil.move(src, dst)
    return json.dumps({"status": "ok", "src": src, "dst": dst})


def _file_delete(arguments: dict) -> str:
    """Delete a file."""
    import os

    path = arguments["path"]
    os.remove(path)
    return json.dumps({"status": "ok", "path": path})
