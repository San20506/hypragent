"""HyprAgent MCP Server — exposes all desktop control tools over stdio.

Connects to: Claude Code, OpenCode, Hermes Agent, or any MCP-compatible client.
Transport: stdio (default). Run with: uv run hypragent

22 tools: screenshots, mouse/keyboard control, OCR, browser automation,
file management, terminal execution, and Hyprland compositor integration.
"""

import asyncio
import json

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
    browser_type, browser_scroll, browser_get_text,
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


def _stub(milestone: str, tool_name: str) -> list[TextContent]:
    return [TextContent(type="text", text=f"[NOT IMPLEMENTED] {tool_name} — implement in {milestone}")]


# ---------------------------------------------------------------------------
# Screenshot tools (M1)
# ---------------------------------------------------------------------------

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
        # ── Hyprland compositor tools (M2.5) ────────────────────────────────
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
        # ── Hyprland compositor tools (M2.5) ────────────────────────────────
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


async def _run() -> None:
    # TODO(06-02): pass real config object once config loader is wired end-to-end
    # For now, DeviceManager.start() will use its built-in defaults (2560×1440)
    devices.start()
    try:
        async with stdio_server() as (read_stream, write_stream):
            await server.run(read_stream, write_stream, server.create_initialization_options())
    finally:
        devices.stop()


def main() -> None:
    asyncio.run(_run())


if __name__ == "__main__":
    main()
