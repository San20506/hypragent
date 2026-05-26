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
from types import SimpleNamespace

import yaml

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from tools.screenshot import capture_fullscreen, capture_region
from tools.mouse import move_mouse, click, drag, scroll
from tools.keyboard import type_text, press_key
from tools.ocr import extract_text_fullscreen, extract_text_from_region
from tools.files import file_list, file_read, file_write, file_move, file_delete
from tools.terminal import terminal_run as _terminal_run
from tools.browser import (
    browser_open, browser_navigate, browser_click,
    browser_type, browser_scroll, browser_get_text, browser_close,
)
from tools.hyprland import (
    workspace_list as _hy_workspace_list,
    workspace_switch as _hy_workspace_switch,
    clients as _hy_clients,
    active_window as _hy_active_window,
    focus_window as _hy_focus_window,
)
from agent.device_manager import devices


server = Server("hypr-agent")

# ── Config ──────────────────────────────────────────────────────────────────

_CONFIG_PATH = os.path.expanduser("~/.config/hypr-agent/config.yaml")
_PROJECT_CONFIG = os.path.join(os.path.dirname(__file__), "config.yaml")


def _dict_to_namespace(d: dict) -> SimpleNamespace:
    """Recursively convert a dict to SimpleNamespace for dotted access."""
    if not isinstance(d, dict):
        return d
    return SimpleNamespace(**{k: _dict_to_namespace(v) for k, v in d.items()})


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


def _detect_screen_resolution() -> tuple[int, int]:
    """Auto-detect screen resolution from hyprctl monitors.

    Returns:
        (width, height) tuple. Falls back to 2560x1440 if detection fails.
    """
    try:
        result = subprocess.run(
            ["hyprctl", "monitors", "-j"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            monitors = json.loads(result.stdout)
            if monitors:
                m = monitors[0]
                return m.get("width", 2560), m.get("height", 1440)
    except (subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError):
        pass
    return 2560, 1440


def _load_config() -> SimpleNamespace:
    """Load config from standard locations.

    Checks:
      1. ~/.config/hypr-agent/config.yaml  (user config)
      2. ./config.yaml                       (project-local)

    Returns a SimpleNamespace with dotted-attribute access.
    Falls back to safe defaults if no config found.
    """
    for path in (_CONFIG_PATH, _PROJECT_CONFIG):
        if os.path.isfile(path):
            with open(path) as f:
                return _dict_to_namespace(yaml.safe_load(f))

    # Sensible defaults — enough for MCP tools to work without a config file
    return _dict_to_namespace({
        "tools": {
            "mouse": {"screen_width": 2560, "screen_height": 1440},
            "keyboard": {"type_delay_ms": 12, "use_clipboard_fallback": True},
        },
        "loop": {"max_steps": 20, "confirm_destructive_actions": True},
        "safety": {"command_blocklist": ["rm -rf /", "dd if=", "mkfs"]},
    })


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
                 "path": {"type": "string"}, "content": {"type": "string"},
                 "confirm": {"type": "boolean", "default": True}
             }, "required": ["path", "content"]}),
        Tool(name="file_move", description="Move or rename a file",
             inputSchema={"type": "object", "properties": {
                 "src": {"type": "string"}, "dst": {"type": "string"},
                 "confirm": {"type": "boolean", "default": True}
             }, "required": ["src", "dst"]}),
        Tool(name="file_delete", description="Delete a file",
             inputSchema={"type": "object", "properties": {
                 "path": {"type": "string"}, "confirm": {"type": "boolean", "default": True}
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
    ]


# ── Tool dispatch ───────────────────────────────────────────────────────────

@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    match name:
        case "take_screenshot":
            try:
                region = arguments.get("region")
                if region:
                    b64 = capture_region(
                        region["x"], region["y"],
                        region["width"], region["height"],
                    )
                else:
                    b64 = capture_fullscreen()
                return [TextContent(type="text", text=b64)]
            except Exception as e:
                return [TextContent(type="text", text=f"Error: {e}")]
        case "mouse_move":
            try:
                move_mouse(arguments["x"], arguments["y"])
                return [TextContent(type="text", text="OK")]
            except Exception as e:
                return [TextContent(type="text", text=f"Error: {e}")]
        case "mouse_click":
            try:
                click(arguments["x"], arguments["y"], arguments.get("button", "left"))
                return [TextContent(type="text", text="OK")]
            except Exception as e:
                return [TextContent(type="text", text=f"Error: {e}")]
        case "mouse_drag":
            try:
                drag(arguments["from_x"], arguments["from_y"],
                     arguments["to_x"], arguments["to_y"])
                return [TextContent(type="text", text="OK")]
            except Exception as e:
                return [TextContent(type="text", text=f"Error: {e}")]
        case "mouse_scroll":
            try:
                scroll(arguments["x"], arguments["y"],
                       arguments["direction"], arguments.get("amount", 3))
                return [TextContent(type="text", text="OK")]
            except Exception as e:
                return [TextContent(type="text", text=f"Error: {e}")]
        case "keyboard_type":
            try:
                type_text(arguments["text"])
                return [TextContent(type="text", text="OK")]
            except Exception as e:
                return [TextContent(type="text", text=f"Error: {e}")]
        case "keyboard_press":
            try:
                press_key(arguments["key"])
                return [TextContent(type="text", text="OK")]
            except Exception as e:
                return [TextContent(type="text", text=f"Error: {e}")]
        case "read_screen_text":
            try:
                region = arguments.get("region")
                if region:
                    text = extract_text_from_region(
                        region["x"], region["y"],
                        region["width"], region["height"],
                    )
                else:
                    text = extract_text_fullscreen()
                return [TextContent(type="text", text=text)]
            except Exception as e:
                return [TextContent(type="text", text=f"Error: {e}")]
        case "browser_open":
            try:
                browser_open(arguments["url"])
                return [TextContent(type="text", text="OK")]
            except Exception as e:
                return [TextContent(type="text", text=f"Error: {e}")]
        case "browser_navigate":
            try:
                browser_navigate(arguments["url"])
                return [TextContent(type="text", text="OK")]
            except Exception as e:
                return [TextContent(type="text", text=f"Error: {e}")]
        case "browser_click":
            try:
                browser_click(arguments["selector"])
                return [TextContent(type="text", text="OK")]
            except Exception as e:
                return [TextContent(type="text", text=f"Error: {e}")]
        case "browser_type":
            try:
                browser_type(arguments["selector"], arguments["text"])
                return [TextContent(type="text", text="OK")]
            except Exception as e:
                return [TextContent(type="text", text=f"Error: {e}")]
        case "browser_scroll":
            try:
                browser_scroll(arguments["direction"], arguments.get("amount", 300))
                return [TextContent(type="text", text="OK")]
            except Exception as e:
                return [TextContent(type="text", text=f"Error: {e}")]
        case "browser_get_text":
            try:
                text = browser_get_text(arguments["selector"])
                return [TextContent(type="text", text=text)]
            except Exception as e:
                return [TextContent(type="text", text=f"Error: {e}")]
        case "browser_close":
            try:
                browser_close()
                return [TextContent(type="text", text="OK")]
            except Exception as e:
                return [TextContent(type="text", text=f"Error: {e}")]
        case "file_list":
            try:
                entries = file_list(arguments["path"])
                return [TextContent(type="text", text=json.dumps(entries))]
            except Exception as e:
                return [TextContent(type="text", text=f"Error: {e}")]
        case "file_read":
            try:
                return [TextContent(type="text", text=file_read(arguments["path"]))]
            except Exception as e:
                return [TextContent(type="text", text=f"Error: {e}")]
        case "file_write":
            try:
                file_write(arguments["path"], arguments["content"],
                           arguments.get("confirm", True))
                return [TextContent(type="text", text="OK")]
            except Exception as e:
                return [TextContent(type="text", text=f"Error: {e}")]
        case "file_move":
            try:
                file_move(arguments["src"], arguments["dst"],
                          arguments.get("confirm", True))
                return [TextContent(type="text", text="OK")]
            except Exception as e:
                return [TextContent(type="text", text=f"Error: {e}")]
        case "file_delete":
            try:
                file_delete(arguments["path"], arguments.get("confirm", True))
                return [TextContent(type="text", text="OK")]
            except Exception as e:
                return [TextContent(type="text", text=f"Error: {e}")]
        case "terminal_run":
            try:
                result = _terminal_run(
                    arguments["command"],
                    cwd=arguments.get("cwd"),
                    timeout=arguments.get("timeout", 30),
                )
                output = result.stdout
                if result.stderr:
                    output += f"\n[stderr]\n{result.stderr}"
                if result.timed_out:
                    output = "[timed out]"
                elif result.returncode != 0:
                    output += f"\n[exit {result.returncode}]"
                return [TextContent(type="text", text=output)]
            except ValueError as e:
                return [TextContent(type="text", text=f"Blocked: {e}")]
            except Exception as e:
                return [TextContent(type="text", text=f"Error: {e}")]
        case "hyprland_workspace_list":
            try:
                data = _hy_workspace_list()
                return [TextContent(type="text", text=json.dumps(data, indent=2))]
            except RuntimeError as e:
                return [TextContent(type="text", text=f"Error: {e}")]
        case "hyprland_workspace_switch":
            try:
                _hy_workspace_switch(arguments["target"])
                return [TextContent(type="text", text="OK")]
            except RuntimeError as e:
                return [TextContent(type="text", text=f"Error: {e}")]
        case "hyprland_clients":
            try:
                data = _hy_clients()
                return [TextContent(type="text", text=json.dumps(data, indent=2))]
            except RuntimeError as e:
                return [TextContent(type="text", text=f"Error: {e}")]
        case "hyprland_active_window":
            try:
                data = _hy_active_window()
                return [TextContent(type="text", text=json.dumps(data, indent=2) if data else "null")]
            except RuntimeError as e:
                return [TextContent(type="text", text=f"Error: {e}")]
        case "hyprland_focus_window":
            try:
                _hy_focus_window(arguments["target"])
                return [TextContent(type="text", text="OK")]
            except RuntimeError as e:
                return [TextContent(type="text", text=f"Error: {e}")]
        case _:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]


# ── Server entry point ──────────────────────────────────────────────────────

async def _run() -> None:
    _detect_hyprland_env()

    config = _load_config()
    screen_w, screen_h = _detect_screen_resolution()

    # Override config defaults with auto-detected resolution if not explicitly set
    try:
        if config.tools.mouse.screen_width == 2560 and config.tools.mouse.screen_height == 1440:
            config.tools.mouse.screen_width = screen_w
            config.tools.mouse.screen_height = screen_h
    except AttributeError:
        pass

    devices.start(config)
    print(f"[HyprAgent] Screen: {screen_w}x{screen_h}", file=sys.stderr)

    try:
        async with stdio_server() as (read_stream, write_stream):
            await server.run(read_stream, write_stream, server.create_initialization_options())
    finally:
        devices.stop()


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
