"""HyprAgent MCP Server — exposes all desktop control tools over stdio.

Connects to: Claude Code, OpenCode, Hermes Agent, or any MCP-compatible client.
Transport: stdio (default). Run with: uv run hypragent

22 tools: screenshots, mouse/keyboard control, OCR, browser automation,
file management, terminal execution, and Hyprland compositor integration.
"""

import argparse
import asyncio
import json
import os
import shutil
import subprocess
import sys

import yaml

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from tools.dispatch import dispatch_tool
from agent.action_executor import execute_plan
from harness import detect_harness


server = Server("hypr-agent")

# ── Config ──────────────────────────────────────────────────────────────────

_CONFIG_PATH = os.path.expanduser("~/.config/hypr-agent/config.yaml")
_PROJECT_CONFIG = os.path.join(os.path.dirname(__file__), "config.yaml")


def _detect_hyprland_env() -> None:
    """Auto-detect Hyprland environment variables if not already set."""
    if os.environ.get("HYPRLAND_INSTANCE_SIGNATURE"):
        return

    hypr_dir = f"/run/user/{os.getuid()}/hypr"
    if not os.path.isdir(hypr_dir):
        return

    try:
        entries = os.listdir(hypr_dir)
        if entries:
            os.environ["HYPRLAND_INSTANCE_SIGNATURE"] = entries[0]
    except OSError:
        pass


def _load_config() -> dict:
    """Load config from standard locations.

    Checks:
      1. ~/.config/hypr-agent/config.yaml  (user config)
      2. ./config.yaml                       (project-local)

    Returns a dict with dotted-attribute access.
    Falls back to safe defaults if no config found.
    """
    for path in (_CONFIG_PATH, _PROJECT_CONFIG):
        if os.path.isfile(path):
            with open(path) as f:
                return yaml.safe_load(f) or {}

    # Sensible defaults — enough for MCP tools to work without a config file
    return {
        "tools": {
            "mouse": {"screen_width": 2560, "screen_height": 1440},
            "keyboard": {"type_delay_ms": 12, "use_clipboard_fallback": True},
        },
        "loop": {"max_steps": 20, "confirm_destructive_actions": True},
        "safety": {"command_blocklist": ["rm -rf /", "dd if=", "mkfs"]},
    }


# ── Doctor (health check) ───────────────────────────────────────────────────

def run_doctor() -> int:
    """Check all system dependencies and report status. Returns exit code."""
    checks = {
        "grim": shutil.which("grim"),
        "hyprctl": shutil.which("hyprctl"),
        "tesseract": shutil.which("tesseract"),
        "wl-copy": shutil.which("wl-copy"),
        "ydotool (optional)": shutil.which("ydotool"),
    }

    all_ok = True
    print("HyprAgent Doctor\n" + "=" * 50)

    for name, path in checks.items():
        status = f"  found ({path})" if path else "  MISSING"
        if not path and "(optional)" not in name:
            all_ok = False
        print(f"  {name:.<30} {status}")

    # Check uinput
    try:
        if os.access("/dev/uinput", os.W_OK):
            print("  /dev/uinput ................... writable")
        else:
            print("  /dev/uinput ................... NOT writable (run: sudo usermod -aG input $USER)")
            all_ok = False
    except OSError:
        print("  /dev/uinput ................... not found (run: sudo modprobe uinput)")
        all_ok = False

    # Check Hyprland
    if checks["hyprctl"]:
        try:
            result = subprocess.run(
                ["hyprctl", "monitors", "-j"],
                capture_output=True, text=True, timeout=5,
            )
            if result.returncode == 0 and result.stdout.strip():
                monitors = json.loads(result.stdout)
                for m in monitors:
                    print(f"  Monitor: {m.get('name', '?')}  "
                          f"{m.get('width', '?')}x{m.get('height', '?')}"
                          f"@{m.get('refreshRate', '?')}Hz")
            else:
                print("  Hyprland ...................... not running or not reachable")
                all_ok = False
        except (subprocess.TimeoutExpired, json.JSONDecodeError):
            print("  Hyprland ...................... not reachable")
            all_ok = False

    # Config
    config_found = os.path.isfile(_CONFIG_PATH) or os.path.isfile(_PROJECT_CONFIG)
    print(f"  config.yaml ................... {'found' if config_found else 'not found (using defaults)'}")

    print()
    if all_ok:
        print("All checks passed.")
        return 0
    else:
        print("Some checks failed. Install missing dependencies:")
        print("  sudo pacman -S grim tesseract tesseract-data-eng wl-clipboard")
        print("  sudo modprobe uinput && sudo usermod -aG input $USER")
        print("  (re-login after adding yourself to the input group)")
        return 1


# ── Tool definitions ────────────────────────────────────────────────────────

@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(name="take_screenshot", description="Capture the current screen or a region of it",
             inputSchema={"type": "object", "properties": {
                 "region": {"type": "object", "properties": {
                     "x": {"type": "integer"}, "y": {"type": "integer"},
                     "width": {"type": "integer"}, "height": {"type": "integer"}
                 }}
             }}),
        Tool(name="mouse_move", description="Move mouse cursor to absolute screen coordinates",
             inputSchema={"type": "object", "properties": {
                 "x": {"type": "integer"}, "y": {"type": "integer"}
             }, "required": ["x", "y"]}),
        Tool(name="mouse_click", description="Move to coordinates and click",
             inputSchema={"type": "object", "properties": {
                 "x": {"type": "integer"}, "y": {"type": "integer"},
                 "button": {"type": "string", "enum": ["left", "right", "middle"], "default": "left"}
             }, "required": ["x", "y"]}),
        Tool(name="mouse_drag", description="Click and drag from one position to another",
             inputSchema={"type": "object", "properties": {
                 "from_x": {"type": "integer"}, "from_y": {"type": "integer"},
                 "to_x": {"type": "integer"}, "to_y": {"type": "integer"}
             }, "required": ["from_x", "from_y", "to_x", "to_y"]}),
        Tool(name="mouse_scroll", description="Scroll at screen coordinates",
             inputSchema={"type": "object", "properties": {
                 "x": {"type": "integer"}, "y": {"type": "integer"},
                 "direction": {"type": "string", "enum": ["up", "down"]},
                 "amount": {"type": "integer", "default": 3}
             }, "required": ["x", "y", "direction"]}),
        Tool(name="keyboard_type", description="Type a string of text",
             inputSchema={"type": "object", "properties": {
                 "text": {"type": "string"}
             }, "required": ["text"]}),
        Tool(name="keyboard_press", description="Press a key or key combination",
             inputSchema={"type": "object", "properties": {
                 "key": {"type": "string", "description": "e.g. Return, Escape, ctrl+c, super+l"}
             }, "required": ["key"]}),
        Tool(name="read_screen_text", description="Extract visible text from screen using OCR",
             inputSchema={"type": "object", "properties": {
                 "region": {"type": "object", "properties": {
                     "x": {"type": "integer"}, "y": {"type": "integer"},
                     "width": {"type": "integer"}, "height": {"type": "integer"}
                 }}
             }}),
        Tool(name="browser_open", description="Open a URL in the browser",
             inputSchema={"type": "object", "properties": {
                 "url": {"type": "string"}
             }, "required": ["url"]}),
        Tool(name="browser_navigate", description="Navigate current browser tab to URL",
             inputSchema={"type": "object", "properties": {
                 "url": {"type": "string"}
             }, "required": ["url"]}),
        Tool(name="browser_click", description="Click a browser element by CSS selector",
             inputSchema={"type": "object", "properties": {
                 "selector": {"type": "string"}
             }, "required": ["selector"]}),
        Tool(name="browser_type", description="Type text into a browser input element",
             inputSchema={"type": "object", "properties": {
                 "selector": {"type": "string"}, "text": {"type": "string"}
             }, "required": ["selector", "text"]}),
        Tool(name="browser_scroll", description="Scroll the current browser page",
             inputSchema={"type": "object", "properties": {
                 "direction": {"type": "string", "enum": ["up", "down"]},
                 "amount": {"type": "integer", "default": 300}
             }, "required": ["direction"]}),
        Tool(name="browser_get_text", description="Get text content of a browser element",
             inputSchema={"type": "object", "properties": {
                 "selector": {"type": "string"}
             }, "required": ["selector"]}),
        Tool(name="browser_close", description="Close the browser and release Playwright resources",
             inputSchema={"type": "object", "properties": {}}),
        Tool(name="file_list", description="List directory contents",
             inputSchema={"type": "object", "properties": {
                 "path": {"type": "string"}
             }, "required": ["path"]}),
        Tool(name="file_read", description="Read a text file",
             inputSchema={"type": "object", "properties": {
                 "path": {"type": "string"}
             }, "required": ["path"]}),
        Tool(name="file_write", description="Write content to a file",
             inputSchema={"type": "object", "properties": {
                 "path": {"type": "string"}, "content": {"type": "string"}
             }, "required": ["path", "content"]}),
        Tool(name="file_move", description="Move or rename a file",
             inputSchema={"type": "object", "properties": {
                 "src": {"type": "string"}, "dst": {"type": "string"}
             }, "required": ["src", "dst"]}),
        Tool(name="file_delete", description="Delete a file",
             inputSchema={"type": "object", "properties": {
                 "path": {"type": "string"}
             }, "required": ["path"]}),
        Tool(name="terminal_run", description="Run a shell command and return output",
             inputSchema={"type": "object", "properties": {
                 "command": {"type": "string"},
                 "cwd": {"type": "string"},
                 "timeout": {"type": "integer", "default": 30}
             }, "required": ["command"]}),
        Tool(name="hyprland_workspace_list",
             description="List all Hyprland workspaces with id, name, window count, monitor, and active flag",
             inputSchema={"type": "object", "properties": {}}),
        Tool(name="hyprland_workspace_switch",
             description="Switch to a workspace by id, name, +1, -1, or 'previous'",
             inputSchema={"type": "object", "properties": {
                 "target": {"type": "string",
                            "description": "Workspace id, name, +1, -1, or 'previous'"}
             }, "required": ["target"]}),
        Tool(name="hyprland_clients",
             description="List all open windows with class, title, pid, workspace, position, and size",
             inputSchema={"type": "object", "properties": {}}),
        Tool(name="hyprland_active_window",
             description="Get the currently focused window (class, title, workspace)",
             inputSchema={"type": "object", "properties": {}}),
        Tool(name="hyprland_focus_window",
             description="Focus a window by class (class:firefox) or address (address:0x...)",
             inputSchema={"type": "object", "properties": {
                 "target": {"type": "string",
                            "description": "Window target: 'class:name' or 'address:0x...'"}
             }, "required": ["target"]}),
        Tool(name="execute_plan",
             description="Execute a batch of actions with dependency-aware parallelism. "
                         "Provide a list of actions, each with id, tool, args, and optional "
                         "depends_on (list of prerequisite action ids). Independent actions "
                         "(read-only queries, compositor commands) run in parallel. Input "
                         "actions (mouse, keyboard) run sequentially. Perception actions "
                         "(screenshot, OCR) run last. Returns results, failures, and a "
                         "verification screenshot with OCR snapshot to confirm effects.",
             inputSchema={"type": "object", "properties": {
                 "actions": {"type": "array", "items": {
                     "type": "object", "properties": {
                         "id": {"type": "string"},
                         "tool": {"type": "string"},
                         "args": {"type": "object"},
                         "depends_on": {"type": "array", "items": {"type": "string"}},
                     }, "required": ["id", "tool", "args"]}},
             }, "required": ["actions"]}),
    ]


# ── Tool dispatch ───────────────────────────────────────────────────────────

@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    try:
        if name == "execute_plan":
            plan_result = execute_plan(arguments["actions"], dispatch_tool, verify=True)
            return [TextContent(type="text", text=json.dumps(plan_result, indent=2))]
        result = dispatch_tool(name, arguments)
        return [TextContent(type="text", text=result)]
    except ValueError as e:
        return [TextContent(type="text", text=f"Blocked: {e}")]
    except Exception as e:
        return [TextContent(type="text", text=f"Error: {e}")]


# ── Server entry point ──────────────────────────────────────────────────────

async def _run() -> None:
    _detect_hyprland_env()

    config = _load_config()

    _harness = detect_harness()
    _harness.start(config)
    # Resolution comes from the harness's own scale-aware detection
    screen_w, screen_h = _harness.screen_resolution()
    print(f"[HyprAgent] Screen: {screen_w}x{screen_h}", file=sys.stderr)

    try:
        async with stdio_server() as (read_stream, write_stream):
            await server.run(read_stream, write_stream, server.create_initialization_options())
    finally:
        _harness.stop()


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="hypragent",
        description="HyprAgent MCP Server — desktop control agent for Hyprland/Wayland",
    )
    parser.add_argument("--version", action="version", version="hypragent 1.0.0")
    parser.add_argument(
        "--doctor", action="store_true",
        help="Check system dependencies and report status",
    )
    args = parser.parse_args()

    if args.doctor:
        sys.exit(run_doctor())

    asyncio.run(_run())


if __name__ == "__main__":
    main()
