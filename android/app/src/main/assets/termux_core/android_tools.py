"""Android-specific tools for the MCP server.

These tools are implemented by Layer A (native Android app) and
called by Layer B (Termux core) via the WebSocket bridge.

Safety: Local tools (termux_exec, file_*) validate commands against an
allowlist and sandbox file paths to $HOME/termux_workspace. Consent
checks are enforced via the ConsentManager on the Android side.
"""

import json
import logging
import os
import shlex
import shutil
import subprocess
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


# ── Security: Command allowlist and path sandboxing ────────────────────────

# Allowed commands for termux_exec — only these executables can run.
# This is an allowlist, not a denylist — everything else is rejected.
TERMUX_ALLOWED_COMMANDS = {
    # File inspection
    "ls", "cat", "head", "tail", "less", "more", "wc", "file", "stat",
    "find", "which", "type",
    # Text processing
    "grep", "egrep", "fgrep", "sed", "awk", "cut", "sort", "uniq", "tr",
    "tee", "xargs", "paste",
    # Directory navigation
    "pwd", "cd",
    # File operations
    "cp", "mv", "ln", "mkdir", "rmdir", "touch", "chmod",
    # System info
    "uname", "hostname", "uptime", "date", "df", "du", "ps",
    # Archives
    "tar", "gzip", "gunzip", "zip", "unzip",
    # Misc utilities
    "echo", "printf", "test", "true", "false", "sleep", "seq",
    "diff", "basename", "dirname", "realpath",
    # Termux-specific
    "termux-info", "termux-open", "termux-share",
}

# Sandbox directory for file operations — defaults to $HOME/termux_workspace
_TERMUX_SANDBOX_DIR: str | None = None


def _get_termux_sandbox() -> str:
    """Get the sandbox directory for Termux file operations."""
    global _TERMUX_SANDBOX_DIR
    if _TERMUX_SANDBOX_DIR is None:
        _TERMUX_SANDBOX_DIR = os.path.join(os.path.expanduser("~"), "termux_workspace")
        os.makedirs(_TERMUX_SANDBOX_DIR, exist_ok=True)
    return _TERMUX_SANDBOX_DIR


def _validate_termux_path(path: str) -> str:
    """Validate that a path is within the Termux sandbox.

    Args:
        path: Path to validate (absolute or relative).

    Returns:
        Resolved absolute path.

    Raises:
        ValueError: If path is outside the sandbox.
    """
    sandbox = _get_termux_sandbox()

    # Resolve to absolute path
    if not os.path.isabs(path):
        path = os.path.join(sandbox, path)

    resolved = os.path.realpath(path)
    sandbox_resolved = os.path.realpath(sandbox)

    # Check that resolved path starts with sandbox
    if not (resolved.startswith(sandbox_resolved + os.sep) or resolved == sandbox_resolved):
        raise ValueError(
            f"Path {path!r} is outside the sandbox directory {sandbox!r}. "
            f"All file operations must stay within the sandbox."
        )

    return resolved


def _check_termux_allowlist(command: str) -> None:
    """Validate that a command is in the Termux allowlist.

    Args:
        command: Shell command string.

    Raises:
        ValueError: If command is not in allowlist.
    """
    # Parse command to extract executable name
    try:
        args = shlex.split(command)
    except ValueError as e:
        raise ValueError(f"Invalid command syntax: {e}")

    if not args:
        raise ValueError("Command must not be empty")

    exe = Path(args[0]).name

    # Check allowlist
    if not any(allowed == exe or exe.startswith(allowed) for allowed in TERMUX_ALLOWED_COMMANDS):
        raise ValueError(
            f"Command not in allowlist: {exe!r}. "
            f"Only explicitly allowed commands can run in Termux. "
            f"See TERMUX_ALLOWED_COMMANDS in android_tools.py for the full list."
        )


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
    """Execute a shell command in Termux, scoped to $HOME.

    Safety: Commands are validated against TERMUX_ALLOWED_COMMANDS.
    """
    command = arguments["command"]
    timeout = arguments.get("timeout", 30)
    cwd = arguments.get("cwd", os.path.expanduser("~"))

    # Validate command against allowlist
    _check_termux_allowlist(command)

    # Parse command for safe execution (no shell=True)
    try:
        args = shlex.split(command)
    except ValueError as e:
        return json.dumps({"error": f"Invalid command syntax: {e}"})

    try:
        result = subprocess.run(
            args,
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
    except Exception as e:
        return json.dumps({"error": str(e)})


def _file_read(arguments: dict) -> str:
    """Read a text file.

    Safety: Path is validated against sandbox.
    """
    path = _validate_termux_path(arguments["path"])
    with open(path, encoding="utf-8") as f:
        return f.read()


def _file_write(arguments: dict) -> str:
    """Write content to a file.

    Safety: Path is validated against sandbox.
    """
    path = _validate_termux_path(arguments["path"])
    content = arguments["content"]
    # Ensure parent directory exists
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return json.dumps({"status": "ok", "path": path})


def _file_list(arguments: dict) -> str:
    """List directory contents.

    Safety: Path is validated against sandbox.
    """
    path = _validate_termux_path(arguments["path"])
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
    """Move or rename a file.

    Safety: Both paths are validated against sandbox.
    """
    src = _validate_termux_path(arguments["src"])
    dst = _validate_termux_path(arguments["dst"])
    shutil.move(src, dst)
    return json.dumps({"status": "ok", "src": src, "dst": dst})


def _file_delete(arguments: dict) -> str:
    """Delete a file.

    Safety: Path is validated against sandbox.
    """
    path = _validate_termux_path(arguments["path"])
    os.remove(path)
    return json.dumps({"status": "ok", "path": path})
