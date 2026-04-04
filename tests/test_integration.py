"""Integration tests for HyprAgent — Milestone M12.

Run non-Wayland tests:
    uv run pytest tests/test_integration.py -m "not wayland" -v

Run all tests (requires Wayland session, grim, ydotoold):
    uv run pytest tests/test_integration.py -v
"""

import base64
import os
import tempfile
from unittest.mock import MagicMock

import pytest

from agent.backends.base import AgentResponse, BackendAdapter
from agent.backends import load_backend
from agent.loop import AgentLoop, AGENT_TOOLS, _dispatch_tool


# ── Imports ───────────────────────────────────────────────────────────────────

def test_all_tool_modules_import():
    from tools import screenshot, mouse, keyboard, ocr, files, terminal, browser
    assert screenshot
    assert mouse
    assert keyboard
    assert ocr
    assert files
    assert terminal
    assert browser


def test_all_backend_modules_import():
    from agent.backends.claude import ClaudeBackend
    from agent.backends.gemini import GeminiBackend
    from agent.backends.ollama import OllamaBackend
    assert ClaudeBackend
    assert GeminiBackend
    assert OllamaBackend


# ── MCP Server ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_mcp_server_lists_25_tools():
    import mcp_server
    tools = await mcp_server.list_tools()
    assert len(tools) == 25
    names = {t.name for t in tools}
    assert "take_screenshot" in names
    assert "terminal_run" in names
    assert "browser_open" in names
    assert "file_write" in names
    assert "read_screen_text" in names
    for hy in ["hyprland_workspace_list", "hyprland_workspace_switch",
               "hyprland_clients", "hyprland_active_window", "hyprland_focus_window"]:
        assert hy in names


# ── File Tools ────────────────────────────────────────────────────────────────

def test_file_write_read_delete():
    from tools.files import file_write, file_read, file_delete
    fd, path = tempfile.mkstemp(suffix=".txt")
    os.close(fd)
    try:
        file_write(path, "integration test", confirm=False)
        assert file_read(path) == "integration test"
    finally:
        if os.path.exists(path):
            file_delete(path, confirm=False)
    assert not os.path.exists(path)


def test_file_list_returns_entries():
    from tools.files import file_list
    entries = file_list(tempfile.gettempdir())
    assert isinstance(entries, list)
    assert len(entries) > 0
    assert all("name" in e and "is_dir" in e and "size" in e for e in entries)


def test_file_write_creates_content():
    from tools.files import file_write, file_read, file_delete
    fd, path = tempfile.mkstemp(suffix=".txt")
    os.close(fd)
    try:
        file_write(path, "hello\nworld", confirm=False)
        assert file_read(path) == "hello\nworld"
    finally:
        os.unlink(path)


# ── Terminal Tool ─────────────────────────────────────────────────────────────

def test_terminal_run_echo():
    from tools.terminal import terminal_run
    result = terminal_run("echo hypr-agent-test")
    assert result.returncode == 0
    assert "hypr-agent-test" in result.stdout
    assert not result.timed_out


def test_terminal_run_error_exit():
    from tools.terminal import terminal_run
    result = terminal_run("ls /nonexistent_hypragent_path_xyz")
    assert result.returncode != 0
    assert not result.timed_out


def test_terminal_run_blocklist():
    from tools.terminal import terminal_run
    with pytest.raises(ValueError, match="blocked"):
        terminal_run("rm -rf /")


def test_terminal_run_blocklist_dd():
    from tools.terminal import terminal_run
    with pytest.raises(ValueError, match="blocked"):
        terminal_run("dd if=/dev/zero of=/dev/sda")


def test_terminal_run_timeout():
    from tools.terminal import terminal_run
    result = terminal_run("sleep 10", timeout=1)
    assert result.timed_out
    assert result.returncode == -1


# ── Backend Factory ───────────────────────────────────────────────────────────

def test_load_backend_claude():
    os.environ.setdefault("ANTHROPIC_API_KEY", "sk-ant-test")
    cfg = {"backend": {"active": "claude", "claude": {
        "model": "claude-sonnet-4-6", "api_key_env": "ANTHROPIC_API_KEY"}}}
    backend = load_backend(cfg)
    assert backend.get_model_name() == "claude-sonnet-4-6"
    assert backend.supports_vision() is True


def test_load_backend_ollama():
    cfg = {"backend": {"active": "ollama", "ollama": {
        "model": "llava", "endpoint": "http://localhost:11434"}}}
    backend = load_backend(cfg)
    assert backend.get_model_name() == "llava"
    assert backend.supports_vision() is True


def test_load_backend_ollama_no_vision():
    cfg = {"backend": {"active": "ollama", "ollama": {
        "model": "mistral", "endpoint": "http://localhost:11434"}}}
    backend = load_backend(cfg)
    assert backend.supports_vision() is False


def test_load_backend_unknown_raises():
    with pytest.raises(ValueError, match="Unknown backend"):
        load_backend({"backend": {"active": "unknown"}})


# ── AGENT_TOOLS ───────────────────────────────────────────────────────────────

def test_agent_tools_count():
    assert len(AGENT_TOOLS) >= 10


def test_agent_tools_schema_valid():
    for tool in AGENT_TOOLS:
        assert "name" in tool, f"Tool missing 'name': {tool}"
        assert "description" in tool, f"Tool missing 'description': {tool}"
        assert "inputSchema" in tool, f"Tool missing 'inputSchema': {tool}"
        assert isinstance(tool["name"], str)


# ── Dispatch Tool ─────────────────────────────────────────────────────────────

def test_dispatch_unknown_tool():
    result = _dispatch_tool("nonexistent_tool", {})
    assert "Unknown tool" in result


def test_dispatch_terminal_run():
    result = _dispatch_tool("terminal_run", {"command": "echo dispatch-test"})
    assert "dispatch-test" in result


def test_dispatch_terminal_blocklist():
    result = _dispatch_tool("terminal_run", {"command": "rm -rf /"})
    assert "Blocked" in result


def test_dispatch_file_write_read():
    fd, path = tempfile.mkstemp(suffix=".txt")
    os.close(fd)
    try:
        write_result = _dispatch_tool("file_write", {"path": path, "content": "dispatch-write"},
                                      config={"loop": {"confirm_destructive_actions": False}})
        assert write_result == "OK"
        read_result = _dispatch_tool("file_read", {"path": path})
        assert read_result == "dispatch-write"
    finally:
        if os.path.exists(path):
            os.unlink(path)


# ── Agent Loop ────────────────────────────────────────────────────────────────

_MOCK_CONFIG = {"loop": {"max_steps": 5, "confirm_destructive_actions": False}}


def test_agent_loop_terminates_on_end_turn():
    mock_backend = MagicMock(spec=BackendAdapter)
    mock_backend.send_message.return_value = AgentResponse(
        content="TASK COMPLETE",
        tool_calls=[],
        stop_reason="end_turn",
    )
    loop = AgentLoop(_MOCK_CONFIG, mock_backend)
    loop.run("test task")
    mock_backend.send_message.assert_called_once()
    assert loop._step == 0  # terminated before incrementing


def test_agent_loop_executes_tool_calls():
    mock_backend = MagicMock(spec=BackendAdapter)
    call_count = 0

    def side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return AgentResponse(
                content="",
                tool_calls=[{"name": "terminal_run",
                             "input": {"command": "echo loop-test"},
                             "id": "id1"}],
                stop_reason="tool_use",
            )
        return AgentResponse(content="done", tool_calls=[], stop_reason="end_turn")

    mock_backend.send_message.side_effect = side_effect
    loop = AgentLoop(_MOCK_CONFIG, mock_backend)
    loop.run("run echo loop-test")
    assert call_count == 2
    # history should contain assistant + tool_result turns
    assert len(loop._history) == 2


def test_agent_loop_terminates_on_max_steps():
    mock_backend = MagicMock(spec=BackendAdapter)
    mock_backend.send_message.return_value = AgentResponse(
        content="",
        tool_calls=[{"name": "keyboard_press", "input": {"key": "Return"}, "id": "id1"}],
        stop_reason="tool_use",
    )
    loop = AgentLoop({"loop": {"max_steps": 2, "confirm_destructive_actions": False}},
                     mock_backend)
    loop.run("keep pressing Enter")
    assert loop._step >= 2


def test_agent_loop_kill_flag():
    mock_backend = MagicMock(spec=BackendAdapter)
    call_count = 0

    def side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        loop._killed = True
        return AgentResponse(
            content="",
            tool_calls=[{"name": "keyboard_press", "input": {"key": "Return"}, "id": "x"}],
            stop_reason="tool_use",
        )

    mock_backend.send_message.side_effect = side_effect
    loop = AgentLoop(_MOCK_CONFIG, mock_backend)
    loop.run("should stop after kill")
    assert call_count == 1


def test_agent_loop_resets_state_on_rerun():
    mock_backend = MagicMock(spec=BackendAdapter)
    mock_backend.send_message.return_value = AgentResponse(
        content="done", tool_calls=[], stop_reason="end_turn"
    )
    loop = AgentLoop(_MOCK_CONFIG, mock_backend)
    loop.run("first run")
    loop._history.append({"role": "user", "content": "stale"})
    loop.run("second run")
    # History should be reset — only new turns from second run
    assert not any(m["content"] == "stale" for m in loop._history)


# ── Wayland-only tests ────────────────────────────────────────────────────────

@pytest.mark.wayland
def test_screenshot_captures_valid_png():
    from tools.screenshot import capture_fullscreen
    b64 = capture_fullscreen()
    assert len(b64) > 1000
    data = base64.b64decode(b64)
    assert data[1:4] == b"PNG"  # PNG magic bytes


@pytest.mark.wayland
def test_screenshot_region():
    from tools.screenshot import capture_region
    b64 = capture_region(0, 0, 200, 200)
    data = base64.b64decode(b64)
    assert data[1:4] == b"PNG"


@pytest.mark.wayland
def test_ocr_fullscreen_returns_text():
    from tools.ocr import extract_text_fullscreen
    text = extract_text_fullscreen()
    assert isinstance(text, str)
    assert len(text) > 0


# ── Hyprland tools — non-wayland (no live Hyprland needed) ───────────────────

def test_hyprland_tools_import():
    from tools.hyprland import (
        workspace_list, workspace_switch, clients,
        active_window, focus_window,
    )
    assert workspace_list
    assert workspace_switch
    assert clients
    assert active_window
    assert focus_window


def test_hyprland_no_instance_raises():
    """Without HYPRLAND_INSTANCE_SIGNATURE, all tools raise RuntimeError."""
    import os
    from unittest.mock import patch
    from tools.hyprland import workspace_list
    env = {k: v for k, v in os.environ.items()
           if k != "HYPRLAND_INSTANCE_SIGNATURE"}
    with patch.dict(os.environ, env, clear=True):
        with pytest.raises(RuntimeError, match="[Hh]yprland"):
            workspace_list()


def test_hyprland_dispatch_no_instance_returns_error():
    """_dispatch_tool returns error string when Hyprland not running."""
    import os
    from unittest.mock import patch
    env = {k: v for k, v in os.environ.items()
           if k != "HYPRLAND_INSTANCE_SIGNATURE"}
    with patch.dict(os.environ, env, clear=True):
        result = _dispatch_tool("hyprland_workspace_list", {})
        assert "Error" in result or "Hyprland" in result


def test_hyprland_agent_tools_present():
    """All 5 hyprland tools are in AGENT_TOOLS."""
    names = {t["name"] for t in AGENT_TOOLS}
    for tool in ["hyprland_workspace_list", "hyprland_workspace_switch",
                 "hyprland_clients", "hyprland_active_window", "hyprland_focus_window"]:
        assert tool in names, f"Missing from AGENT_TOOLS: {tool}"


def test_hyprland_agent_tools_schema_valid():
    """All hyprland AGENT_TOOLS entries have required schema fields."""
    hy_tools = [t for t in AGENT_TOOLS if t["name"].startswith("hyprland")]
    assert len(hy_tools) == 5
    for tool in hy_tools:
        assert "name" in tool
        assert "description" in tool
        assert "inputSchema" in tool


# ── Hyprland tools — wayland-live (requires running Hyprland) ────────────────

@pytest.mark.wayland
def test_hyprland_workspace_list_live():
    from tools.hyprland import workspace_list
    workspaces = workspace_list()
    assert isinstance(workspaces, list)
    assert len(workspaces) > 0
    ws = workspaces[0]
    assert "id" in ws
    assert "name" in ws
    assert "windows" in ws
    assert "active" in ws
    assert isinstance(ws["active"], bool)
    # Exactly one workspace should be active
    assert sum(1 for w in workspaces if w["active"]) == 1


@pytest.mark.wayland
def test_hyprland_clients_live():
    from tools.hyprland import clients
    result = clients()
    assert isinstance(result, list)
    for c in result:
        assert "class_" in c
        assert "title" in c
        assert "workspace_id" in c
        assert "pid" in c
        assert isinstance(c["floating"], bool)


@pytest.mark.wayland
def test_hyprland_active_window_live():
    from tools.hyprland import active_window
    result = active_window()
    # May be None (empty desktop) or a dict
    assert result is None or isinstance(result, dict)
    if result is not None:
        assert "class_" in result
        assert "title" in result
        assert "workspace_id" in result
