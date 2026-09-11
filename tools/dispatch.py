"""Shared tool dispatch — single source of truth for all MCP tool routing.

Safety: All tool arguments are validated before dispatch. Required parameters
are checked for presence and type. Numeric parameters are bounds-checked.
"""

import json
import platform
import time
from collections import defaultdict

# ── Rate limiting ────────────────────────────────────────────────────────────

class RateLimiter:
    """Simple token bucket rate limiter."""

    def __init__(self, max_calls: int, period: float):
        """Initialize rate limiter.

        Args:
            max_calls: Maximum number of calls allowed per period.
            period: Time period in seconds.
        """
        self.max_calls = max_calls
        self.period = period
        self.calls = defaultdict(list)

    def check(self, key: str) -> bool:
        """Check if a call is allowed.

        Args:
            key: Identifier for the rate limit bucket (e.g. tool name).

        Returns:
            True if call is allowed, False if rate limit exceeded.
        """
        now = time.time()
        # Remove old calls outside the period
        self.calls[key] = [t for t in self.calls[key] if now - t < self.period]
        # Check if under limit
        if len(self.calls[key]) >= self.max_calls:
            return False
        # Record this call
        self.calls[key].append(now)
        return True


# Rate limits per tool (calls per second)
_RATE_LIMITS = {
    "terminal_run": (10, 1.0),  # 10 commands per second
    "file_write": (100, 1.0),   # 100 writes per second
    "file_delete": (100, 1.0),  # 100 deletes per second
    "file_move": (100, 1.0),    # 100 moves per second
}

_rate_limiters = {
    tool: RateLimiter(max_calls, period)
    for tool, (max_calls, period) in _RATE_LIMITS.items()
}


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


def _is_windows() -> bool:
    return platform.system() == "Windows"


class ToolValidationError(Exception):
    """Raised when tool arguments fail validation."""
    pass


def _require_arg(args: dict, name: str, expected_type: type | tuple[type, ...]) -> any:
    """Get a required argument with type checking.

    Args:
        args: Tool arguments dict.
        name: Argument name.
        expected_type: Expected type or tuple of types.

    Returns:
        Argument value.

    Raises:
        ToolValidationError: If argument is missing or wrong type.
    """
    if name not in args:
        raise ToolValidationError(f"Missing required argument: {name!r}")
    value = args[name]
    if not isinstance(value, expected_type):
        type_name = expected_type.__name__ if isinstance(expected_type, type) else " or ".join(t.__name__ for t in expected_type)
        raise ToolValidationError(
            f"Argument {name!r} must be {type_name}, got {type(value).__name__}"
        )
    return value


def _optional_arg(args: dict, name: str, expected_type: type | tuple[type, ...], default: any) -> any:
    """Get an optional argument with type checking and default.

    Args:
        args: Tool arguments dict.
        name: Argument name.
        expected_type: Expected type or tuple of types.
        default: Default value if argument is missing.

    Returns:
        Argument value or default.

    Raises:
        ToolValidationError: If argument is present but wrong type.
    """
    if name not in args:
        return default
    value = args[name]
    if not isinstance(value, expected_type):
        type_name = expected_type.__name__ if isinstance(expected_type, type) else " or ".join(t.__name__ for t in expected_type)
        raise ToolValidationError(
            f"Argument {name!r} must be {type_name}, got {type(value).__name__}"
        )
    return value


def _validate_coordinate(value: int, name: str, max_value: int | None = None) -> int:
    """Validate a coordinate value.

    Args:
        value: Coordinate value.
        name: Argument name for error messages.
        max_value: Maximum allowed value (optional).

    Returns:
        Validated coordinate.

    Raises:
        ToolValidationError: If coordinate is out of bounds.
    """
    if value < 0:
        raise ToolValidationError(f"Coordinate {name!r} must be non-negative, got {value}")
    if max_value is not None and value > max_value:
        raise ToolValidationError(
            f"Coordinate {name!r} exceeds maximum {max_value}, got {value}"
        )
    return value


def dispatch_tool(tool_name: str, args: dict) -> str:
    """Execute a tool by name and return the result as a string.

    Args:
        tool_name: Name of the tool to execute.
        args: Tool arguments dict.

    Returns:
        Tool result as string.

    Raises:
        ToolValidationError: If arguments fail validation.
    """
    try:
        # Check rate limit
        if tool_name in _rate_limiters:
            if not _rate_limiters[tool_name].check(tool_name):
                return f"Rate limit exceeded for {tool_name}. Please wait before retrying."

        match tool_name:
            case "take_screenshot":
                region = args.get("region")
                if region:
                    x = _require_arg(region, "x", int)
                    y = _require_arg(region, "y", int)
                    width = _require_arg(region, "width", int)
                    height = _require_arg(region, "height", int)
                    _validate_coordinate(x, "region.x")
                    _validate_coordinate(y, "region.y")
                    _validate_coordinate(width, "region.width")
                    _validate_coordinate(height, "region.height")
                    return capture_region(x, y, width, height)
                return capture_fullscreen()
            case "mouse_move":
                x = _require_arg(args, "x", int)
                y = _require_arg(args, "y", int)
                _validate_coordinate(x, "x")
                _validate_coordinate(y, "y")
                move_mouse(x, y)
                return "OK"
            case "mouse_click":
                x = _require_arg(args, "x", int)
                y = _require_arg(args, "y", int)
                button = _optional_arg(args, "button", str, "left")
                _validate_coordinate(x, "x")
                _validate_coordinate(y, "y")
                if button not in {"left", "right", "middle"}:
                    raise ToolValidationError(f"Invalid button: {button!r}")
                click(x, y, button)
                return "OK"
            case "mouse_drag":
                from_x = _require_arg(args, "from_x", int)
                from_y = _require_arg(args, "from_y", int)
                to_x = _require_arg(args, "to_x", int)
                to_y = _require_arg(args, "to_y", int)
                _validate_coordinate(from_x, "from_x")
                _validate_coordinate(from_y, "from_y")
                _validate_coordinate(to_x, "to_x")
                _validate_coordinate(to_y, "to_y")
                drag(from_x, from_y, to_x, to_y)
                return "OK"
            case "mouse_scroll":
                x = _require_arg(args, "x", int)
                y = _require_arg(args, "y", int)
                direction = _require_arg(args, "direction", str)
                amount = _optional_arg(args, "amount", int, 3)
                _validate_coordinate(x, "x")
                _validate_coordinate(y, "y")
                if direction not in {"up", "down"}:
                    raise ToolValidationError(f"Invalid direction: {direction!r}")
                if amount < 0:
                    raise ToolValidationError(f"Scroll amount must be non-negative, got {amount}")
                scroll(x, y, direction, amount)
                return "OK"
            case "keyboard_type":
                text = _require_arg(args, "text", str)
                type_text(text)
                return "OK"
            case "keyboard_press":
                key = _require_arg(args, "key", str)
                press_key(key)
                return "OK"
            case "read_screen_text":
                region = args.get("region")
                if region:
                    x = _require_arg(region, "x", int)
                    y = _require_arg(region, "y", int)
                    width = _require_arg(region, "width", int)
                    height = _require_arg(region, "height", int)
                    _validate_coordinate(x, "region.x")
                    _validate_coordinate(y, "region.y")
                    _validate_coordinate(width, "region.width")
                    _validate_coordinate(height, "region.height")
                    return extract_text_from_region(x, y, width, height)
                return extract_text_fullscreen()
            case "browser_open" | "browser_navigate":
                url = _require_arg(args, "url", str)
                browser_open(url)
                return "OK"
            case "browser_click":
                selector = _require_arg(args, "selector", str)
                browser_click(selector)
                return "OK"
            case "browser_type":
                selector = _require_arg(args, "selector", str)
                text = _require_arg(args, "text", str)
                browser_type(selector, text)
                return "OK"
            case "browser_scroll":
                direction = _require_arg(args, "direction", str)
                amount = _optional_arg(args, "amount", int, 300)
                if direction not in {"up", "down"}:
                    raise ToolValidationError(f"Invalid direction: {direction!r}")
                if amount < 0:
                    raise ToolValidationError(f"Scroll amount must be non-negative, got {amount}")
                browser_scroll(direction, amount)
                return "OK"
            case "browser_get_text":
                selector = _require_arg(args, "selector", str)
                return browser_get_text(selector)
            case "browser_close":
                browser_close()
                return "OK"
            case "file_list":
                path = _require_arg(args, "path", str)
                return json.dumps(file_list(path))
            case "file_read":
                path = _require_arg(args, "path", str)
                return file_read(path)
            case "file_write":
                path = _require_arg(args, "path", str)
                content = _require_arg(args, "content", str)
                file_write(path, content)
                return "OK"
            case "file_move":
                src = _require_arg(args, "src", str)
                dst = _require_arg(args, "dst", str)
                file_move(src, dst)
                return "OK"
            case "file_delete":
                path = _require_arg(args, "path", str)
                file_delete(path)
                return "OK"
            case "terminal_run":
                command = _require_arg(args, "command", str)
                cwd = _optional_arg(args, "cwd", str, None)
                timeout = _optional_arg(args, "timeout", int, 30)
                if timeout < 0:
                    raise ToolValidationError(f"Timeout must be non-negative, got {timeout}")
                result = _terminal_run(command, cwd=cwd, timeout=timeout)
                output = result.stdout
                if result.stderr:
                    output += "\n[stderr]\n" + result.stderr
                if result.timed_out:
                    output = "[timed out]"
                elif result.returncode != 0:
                    output += "\n[exit " + str(result.returncode) + "]"
                return output
            # Compositor tools — platform-specific prefix, same harness backend
            case "hyprland_workspace_list" | "windows_workspace_list":
                return json.dumps(_hy_workspace_list(), indent=2)
            case "hyprland_workspace_switch" | "windows_workspace_switch":
                target = _require_arg(args, "target", (int, str))
                _hy_workspace_switch(target)
                return "OK"
            case "hyprland_clients" | "windows_clients":
                return json.dumps(_hy_clients(), indent=2)
            case "hyprland_active_window" | "windows_active_window":
                data = _hy_active_window()
                return json.dumps(data, indent=2) if data else "null"
            case "hyprland_focus_window" | "windows_focus_window":
                target = _require_arg(args, "target", str)
                _hy_focus_window(target)
                return "OK"
            case _:
                return "Unknown tool: " + tool_name
    except ToolValidationError as e:
        return f"Validation error: {e}"
