"""Hyprland compositor tools. Milestone M2.5.

Queries and controls the Hyprland window manager via hyprctl.
Requires: hyprctl (ships with Hyprland), HYPRLAND_INSTANCE_SIGNATURE env var.

System dependency: hyprland (pacman -S hyprland)
No additional daemons or packages required.
"""

import json
import os
import subprocess


def _check_hyprland() -> None:
    """Raise RuntimeError if not running under Hyprland."""
    if not os.environ.get("HYPRLAND_INSTANCE_SIGNATURE"):
        raise RuntimeError(
            "Not running under Hyprland "
            "(HYPRLAND_INSTANCE_SIGNATURE not set)"
        )


def _hyprctl(*args: str) -> str:
    """Run hyprctl with given args and return stdout.

    Raises:
        RuntimeError: If hyprctl exits non-zero.
        RuntimeError: If hyprctl binary is not found.
    """
    _check_hyprland()
    try:
        result = subprocess.run(
            ["hyprctl", *args],
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        raise RuntimeError("hyprctl not found — is hyprland installed?")
    if result.returncode != 0:
        raise RuntimeError(f"hyprctl failed: {result.stderr.strip()}")
    return result.stdout


def workspace_list() -> list[dict]:
    """Return all workspaces with id, name, windows, monitor, active.

    Returns:
        List of dicts, each with keys:
            id (int), name (str), windows (int), monitor (str), active (bool)
    """
    raw = json.loads(_hyprctl("workspaces", "-j"))
    active_raw = json.loads(_hyprctl("activeworkspace", "-j"))
    active_id = active_raw.get("id")
    return [
        {
            "id": ws["id"],
            "name": ws["name"],
            "windows": ws.get("windows", 0),
            "monitor": ws.get("monitor", ""),
            "active": ws["id"] == active_id,
        }
        for ws in raw
    ]


def workspace_switch(target: str | int) -> None:
    """Switch to a workspace by id, name, +1, -1, or 'previous'.

    Args:
        target: Workspace id (int or str), "+1", "-1", "previous", or name.

    Raises:
        RuntimeError: If hyprctl dispatch fails.
    """
    _hyprctl("dispatch", "workspace", str(target))


def clients() -> list[dict]:
    """Return all open windows with class, title, pid, position, size.

    Returns:
        List of dicts, each with keys:
            address (str), class_ (str), title (str), pid (int),
            workspace_id (int), workspace_name (str),
            x (int), y (int), width (int), height (int),
            floating (bool), fullscreen (bool)
    """
    raw = json.loads(_hyprctl("clients", "-j"))
    return [
        {
            "address": c.get("address", ""),
            "class_": c.get("class", ""),
            "title": c.get("title", ""),
            "pid": c.get("pid", 0),
            "workspace_id": c.get("workspace", {}).get("id", 0),
            "workspace_name": c.get("workspace", {}).get("name", ""),
            "x": c.get("at", [0, 0])[0],
            "y": c.get("at", [0, 0])[1],
            "width": c.get("size", [0, 0])[0],
            "height": c.get("size", [0, 0])[1],
            "floating": bool(c.get("floating", False)),
            "fullscreen": bool(c.get("fullscreen", False)),
        }
        for c in raw
    ]


def active_window() -> dict | None:
    """Return the currently focused window, or None if no window is focused.

    Returns:
        Dict with keys: address, class_, title, workspace_id, workspace_name
        None if no window is focused (empty desktop).
    """
    raw = json.loads(_hyprctl("activewindow", "-j"))
    # Hyprland returns {"message": "Invalid"} or similar when no window is active
    if not raw or raw.get("message") == "Invalid" or not raw.get("address"):
        return None
    return {
        "address": raw.get("address", ""),
        "class_": raw.get("class", ""),
        "title": raw.get("title", ""),
        "workspace_id": raw.get("workspace", {}).get("id", 0),
        "workspace_name": raw.get("workspace", {}).get("name", ""),
    }


def focus_window(target: str) -> None:
    """Focus a window by class or address.

    Args:
        target: Window target. Formats:
            - "class:firefox"   — focus by window class
            - "address:0x..."   — focus by window address
            - "firefox"         — bare name, treated as class:firefox

    Raises:
        RuntimeError: If hyprctl dispatch fails.
    """
    if ":" not in target:
        target = f"class:{target}"
    _hyprctl("dispatch", "focuswindow", target)
