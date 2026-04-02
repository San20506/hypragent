"""HyprAgent MCP Server — exposes all desktop control tools over stdio.

Connects to: Claude Code, OpenCode, or any MCP-compatible client.
Transport: stdio (default). Run with: uv run hypragent

All tool handlers call stub implementations until milestones M1-M9 are complete.
Stubs return an informative message rather than raising, so the server stays alive.
"""

import asyncio

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from tools.screenshot import capture_fullscreen, capture_region


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
            return _stub("M2", name)
        case "mouse_click":
            return _stub("M2", name)
        case "mouse_drag":
            return _stub("M2", name)
        case "mouse_scroll":
            return _stub("M2", name)
        case "keyboard_type":
            return _stub("M2", name)
        case "keyboard_press":
            return _stub("M2", name)
        case "read_screen_text":
            return _stub("M3", name)
        case "browser_open":
            return _stub("M7", name)
        case "browser_navigate":
            return _stub("M7", name)
        case "browser_click":
            return _stub("M7", name)
        case "browser_type":
            return _stub("M7", name)
        case "browser_scroll":
            return _stub("M7", name)
        case "browser_get_text":
            return _stub("M7", name)
        case "file_list":
            return _stub("M8", name)
        case "file_read":
            return _stub("M8", name)
        case "file_write":
            return _stub("M8", name)
        case "file_move":
            return _stub("M8", name)
        case "file_delete":
            return _stub("M8", name)
        case "terminal_run":
            return _stub("M9", name)
        case _:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]


def main() -> None:
    asyncio.run(stdio_server(server))


if __name__ == "__main__":
    main()
