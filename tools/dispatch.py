"""Shared tool dispatch — single source of truth for all MCP tool routing."""

import json

from tools.screenshot import capture_fullscreen, capture_region
from tools.mouse import move_mouse, click, drag, scroll
from tools.keyboard import type_text, press_key
from tools.ocr import extract_text_fullscreen, extract_text_from_region
from tools.files import file_list, file_read, file_write, file_move, file_delete
from tools.terminal import terminal_run as _terminal_run
from tools.browser import (
    browser_open, browser_click,
    browser_type, browser_scroll, browser_get_text, browser_close,
)
from tools.hyprland import (
    workspace_list as _hy_workspace_list,
    workspace_switch as _hy_workspace_switch,
    clients as _hy_clients,
    active_window as _hy_active_window,
    focus_window as _hy_focus_window,
)


def dispatch_tool(tool_name: str, args: dict) -> str:
    """Execute a tool by name and return the result as a string."""
    match tool_name:
        case "take_screenshot":
            region = args.get("region")
            if region:
                return capture_region(
                    region["x"], region["y"],
                    region["width"], region["height"],
                )
            return capture_fullscreen()
        case "mouse_move":
            move_mouse(args["x"], args["y"])
            return "OK"
        case "mouse_click":
            click(args["x"], args["y"], args.get("button", "left"))
            return "OK"
        case "mouse_drag":
            drag(args["from_x"], args["from_y"],
                 args["to_x"], args["to_y"])
            return "OK"
        case "mouse_scroll":
            scroll(args["x"], args["y"],
                   args["direction"], args.get("amount", 3))
            return "OK"
        case "keyboard_type":
            type_text(args["text"])
            return "OK"
        case "keyboard_press":
            press_key(args["key"])
            return "OK"
        case "read_screen_text":
            region = args.get("region")
            if region:
                return extract_text_from_region(
                    region["x"], region["y"],
                    region["width"], region["height"],
                )
            return extract_text_fullscreen()
        case "browser_open" | "browser_navigate":
            browser_open(args["url"])
            return "OK"
        case "browser_click":
            browser_click(args["selector"])
            return "OK"
        case "browser_type":
            browser_type(args["selector"], args["text"])
            return "OK"
        case "browser_scroll":
            browser_scroll(args["direction"], args.get("amount", 300))
            return "OK"
        case "browser_get_text":
            return browser_get_text(args["selector"])
        case "browser_close":
            browser_close()
            return "OK"
        case "file_list":
            return json.dumps(file_list(args["path"]))
        case "file_read":
            return file_read(args["path"])
        case "file_write":
            file_write(args["path"], args["content"])
            return "OK"
        case "file_move":
            file_move(args["src"], args["dst"])
            return "OK"
        case "file_delete":
            file_delete(args["path"])
            return "OK"
        case "terminal_run":
            result = _terminal_run(
                args["command"],
                cwd=args.get("cwd"),
                timeout=args.get("timeout", 30),
            )
            output = result.stdout
            if result.stderr:
                output += "\n[stderr]\n" + result.stderr
            if result.timed_out:
                output = "[timed out]"
            elif result.returncode != 0:
                output += "\n[exit " + str(result.returncode) + "]"
            return output
        case "hyprland_workspace_list":
            return json.dumps(_hy_workspace_list(), indent=2)
        case "hyprland_workspace_switch":
            _hy_workspace_switch(args["target"])
            return "OK"
        case "hyprland_clients":
            return json.dumps(_hy_clients(), indent=2)
        case "hyprland_active_window":
            data = _hy_active_window()
            return json.dumps(data, indent=2) if data else "null"
        case "hyprland_focus_window":
            _hy_focus_window(args["target"])
            return "OK"
        case _:
            return "Unknown tool: " + tool_name
