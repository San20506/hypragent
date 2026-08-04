"""Integration tests for HyprAgent — Milestone M12.

Run non-Wayland tests:
    uv run pytest tests/test_integration.py -m "not wayland" -v

Run all tests (requires Wayland session, grim, /dev/uinput):
    uv run pytest tests/test_integration.py -v
"""

import base64
import os
import platform
import tempfile
from unittest.mock import MagicMock

import pytest

from agent.backends.base import AgentResponse, BackendAdapter
from agent.backends import load_backend
from agent.loop import AgentLoop, AGENT_TOOLS, _dispatch_tool

_IS_WINDOWS = platform.system() == "Windows"


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
async def test_mcp_server_lists_tools():
    import mcp_server
    tools = await mcp_server.list_tools()
    assert len(tools) >= 25
    names = {t.name for t in tools}
    assert "take_screenshot" in names
    assert "terminal_run" in names
    assert "browser_open" in names
    assert "file_write" in names
    assert "read_screen_text" in names
    if _IS_WINDOWS:
        for w in ["windows_workspace_list", "windows_workspace_switch",
                   "windows_clients", "windows_active_window", "windows_focus_window"]:
            assert w in names
    else:
        for hy in ["hyprland_workspace_list", "hyprland_workspace_switch",
                   "hyprland_clients", "hyprland_active_window", "hyprland_focus_window"]:
            assert hy in names


# ── File Tools ────────────────────────────────────────────────────────────────

def test_file_write_read_delete():
    from tools.files import file_write, file_read, file_delete
    fd, path = tempfile.mkstemp(suffix=".txt")
    os.close(fd)
    try:
        file_write(path, "integration test")
        assert file_read(path) == "integration test"
    finally:
        if os.path.exists(path):
            file_delete(path)
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
        file_write(path, "hello\nworld")
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
    if _IS_WINDOWS:
        with pytest.raises(ValueError, match="blocked"):
            terminal_run("format C:")
    else:
        with pytest.raises(ValueError, match="blocked"):
            terminal_run("rm -rf /")


def test_terminal_run_blocklist_dd():
    from tools.terminal import terminal_run
    with pytest.raises(ValueError, match="blocked"):
        terminal_run("dd if=/dev/zero of=/dev/sda")


def test_terminal_run_timeout():
    from tools.terminal import terminal_run
    if _IS_WINDOWS:
        result = terminal_run("ping -n 10 127.0.0.1", timeout=1)
    else:
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
    if _IS_WINDOWS:
        with pytest.raises(ValueError, match="blocked"):
            _dispatch_tool("terminal_run", {"command": "format C:"})
    else:
        result = _dispatch_tool("terminal_run", {"command": "rm -rf /"})
        assert "Blocked" in result or "blocked" in result


def test_dispatch_file_write_read():
    fd, path = tempfile.mkstemp(suffix=".txt")
    os.close(fd)
    try:
        write_result = _dispatch_tool("file_write", {"path": path, "content": "dispatch-write"})
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
    if _IS_WINDOWS:
        pytest.skip("Hyprland-specific test")
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
    if _IS_WINDOWS:
        pytest.skip("Hyprland-specific test")
    import os
    from unittest.mock import patch
    env = {k: v for k, v in os.environ.items()
           if k != "HYPRLAND_INSTANCE_SIGNATURE"}
    with patch.dict(os.environ, env, clear=True):
        result = _dispatch_tool("hyprland_workspace_list", {})
        assert "Error" in result or "Hyprland" in result


def test_hyprland_agent_tools_present():
    """All 5 hyprland tools are in AGENT_TOOLS."""
    if _IS_WINDOWS:
        pytest.skip("Hyprland-specific test")
    names = {t["name"] for t in AGENT_TOOLS}
    for tool in ["hyprland_workspace_list", "hyprland_workspace_switch",
                 "hyprland_clients", "hyprland_active_window", "hyprland_focus_window"]:
        assert tool in names, f"Missing from AGENT_TOOLS: {tool}"


def test_hyprland_agent_tools_schema_valid():
    """All hyprland AGENT_TOOLS entries have required schema fields."""
    if _IS_WINDOWS:
        pytest.skip("Hyprland-specific test")
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


# ── Windows harness tests ───────────────────────────────────────────────────

@pytest.mark.windows
def test_windows_harness_starts():
    from harness.windows import WindowsHarness
    h = WindowsHarness()
    h.start()
    assert h._started
    h.stop()
    assert not h._started


@pytest.mark.windows
def test_windows_harness_verify():
    from harness.windows import WindowsHarness
    h = WindowsHarness()
    h.start()
    info = h.verify()
    assert info["name"] == "windows"
    assert info["started"] is True
    assert "resolution" in info
    h.stop()


@pytest.mark.windows
def test_windows_screenshot_valid_png():
    from harness.windows import WindowsHarness
    h = WindowsHarness()
    h.start()
    b64 = h.capture_fullscreen()
    assert len(b64) > 1000
    data = base64.b64decode(b64)
    assert data[1:4] == b"PNG"
    h.stop()


@pytest.mark.windows
def test_windows_screenshot_region():
    from harness.windows import WindowsHarness
    h = WindowsHarness()
    h.start()
    b64 = h.capture_region(0, 0, 200, 200)
    data = base64.b64decode(b64)
    assert data[1:4] == b"PNG"
    h.stop()


@pytest.mark.windows
def test_windows_screenshot_invalid_region():
    from harness.windows import WindowsHarness
    h = WindowsHarness()
    h.start()
    with pytest.raises(ValueError):
        h.capture_region(0, 0, 0, 100)
    with pytest.raises(ValueError):
        h.capture_region(0, 0, 100, -1)
    h.stop()


@pytest.mark.windows
def test_windows_screen_resolution():
    from harness.windows import WindowsHarness
    h = WindowsHarness()
    h.start()
    w, h_res = h.screen_resolution()
    assert w > 0
    assert h_res > 0
    h.stop()


@pytest.mark.windows
def test_windows_mouse_move_no_crash():
    """move_mouse should not raise — actual position verification needs a display."""
    from harness.windows import WindowsHarness
    h = WindowsHarness()
    h.start()
    h.move_mouse(500, 500)
    h.stop()


@pytest.mark.windows
def test_windows_click_invalid_button():
    from harness.windows import WindowsHarness
    h = WindowsHarness()
    h.start()
    with pytest.raises(ValueError, match="Unknown button"):
        h.click(100, 100, button="invalid")
    h.stop()


@pytest.mark.windows
def test_windows_type_text_empty_raises():
    from harness.windows import WindowsHarness
    h = WindowsHarness()
    h.start()
    with pytest.raises(ValueError, match="must not be empty"):
        h.type_text("")
    h.stop()


@pytest.mark.windows
def test_windows_press_key_unknown_modifier():
    from harness.windows import WindowsHarness
    h = WindowsHarness()
    h.start()
    with pytest.raises(ValueError, match="Unknown modifier"):
        h.press_key("badmod+a")
    h.stop()


@pytest.mark.windows
def test_windows_press_key_unknown_key():
    from harness.windows import WindowsHarness
    h = WindowsHarness()
    h.start()
    with pytest.raises(ValueError, match="Unknown key"):
        h.press_key("badkeyname")
    h.stop()


@pytest.mark.windows
def test_windows_hotkey_empty_raises():
    from harness.windows import WindowsHarness
    h = WindowsHarness()
    h.start()
    with pytest.raises(ValueError, match="at least one key"):
        h.hotkey()
    h.stop()


@pytest.mark.windows
def test_windows_window_list():
    from harness.windows import WindowsHarness
    h = WindowsHarness()
    h.start()
    clients = h.clients()
    assert isinstance(clients, list)
    # There should be at least one visible window on any Windows desktop
    assert len(clients) > 0
    for c in clients:
        assert "hwnd" in c
        assert "title" in c
        assert "class_" in c
    h.stop()


@pytest.mark.windows
def test_windows_active_window():
    from harness.windows import WindowsHarness
    h = WindowsHarness()
    h.start()
    result = h.active_window()
    # May be None in rare cases (no foreground window)
    if result is not None:
        assert isinstance(result, dict)
        assert "hwnd" in result
        assert "title" in result
    h.stop()


@pytest.mark.windows
def test_windows_workspace_list():
    from harness.windows import WindowsHarness
    h = WindowsHarness()
    h.start()
    workspaces = h.workspace_list()
    assert isinstance(workspaces, list)
    assert len(workspaces) > 0
    assert workspaces[0]["active"] is True
    h.stop()


@pytest.mark.windows
def test_windows_detect_harness():
    """detect_harness() should return WindowsHarness on Windows."""
    import platform
    if platform.system() != "Windows":
        pytest.skip("Windows only")
    from harness import detect_harness, reset_harness
    reset_harness()
    h = detect_harness()
    assert h.name == "windows"
    reset_harness()


# ── Windows dispatch tests ──────────────────────────────────────────────────

@pytest.mark.windows
def test_dispatch_windows_tools():
    """windows_* tool names should dispatch correctly."""
    from agent.loop import _dispatch_tool
    result = _dispatch_tool("windows_workspace_list", {})
    # Should return JSON, not "Unknown tool"
    assert "Unknown tool" not in result


@pytest.mark.windows
def test_dispatch_windows_clients():
    from agent.loop import _dispatch_tool
    result = _dispatch_tool("windows_clients", {})
    assert "Unknown tool" not in result


@pytest.mark.windows
def test_dispatch_windows_active_window():
    from agent.loop import _dispatch_tool
    result = _dispatch_tool("windows_active_window", {})
    assert "Unknown tool" not in result


# ── HiDPI screenshot scaling ─────────────────────────────────────────────────

def test_scale_screenshot_noop_for_small():
    import base64, io
    from PIL import Image
    from agent.loop import scale_screenshot
    img = Image.new("RGB", (800, 600), (0, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    scaled, factor = scale_screenshot(b64, 1024, 768)
    assert scaled == b64
    assert factor == 1.0


def test_scale_screenshot_scales_down():
    import base64, io
    from PIL import Image
    from agent.loop import scale_screenshot
    img = Image.new("RGB", (3840, 2160), (0, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    scaled, factor = scale_screenshot(b64, 1024, 768)
    out = Image.open(io.BytesIO(base64.b64decode(scaled)))
    assert out.width <= 1024
    assert out.height <= 768
    # Scale factor maps scaled width back to native width
    assert round(out.width * factor) == 3840
    assert round(out.height * factor) == 2160


def test_scale_screenshot_preserves_aspect():
    import base64, io
    from PIL import Image
    from agent.loop import scale_screenshot
    img = Image.new("RGB", (1920, 1080), (0, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    scaled, factor = scale_screenshot(b64, 1024, 768)
    out = Image.open(io.BytesIO(base64.b64decode(scaled)))
    assert out.width / out.height == pytest.approx(1920 / 1080, rel=0.01)
    assert factor > 1.0


def test_loop_scales_mouse_coordinates():
    """With scale != 1.0, mouse coords are converted back to native pixels."""
    from unittest.mock import patch
    from agent.loop import AgentLoop, MOUSE_COORD_TOOLS
    mock_backend = MagicMock(spec=BackendAdapter)
    loop = AgentLoop({"loop": {"confirm_destructive_actions": False}}, mock_backend)
    loop._scale_factor = 2.0
    loop._dispatch = MagicMock(return_value="OK")
    # Patch module-level _dispatch_tool used by _act
    with patch("agent.loop._dispatch_tool", return_value="OK") as mock_dispatch:
        loop._act(AgentResponse(
            content="",
            tool_calls=[{"name": "mouse_move", "input": {"x": 512, "y": 384}, "id": "m1"}],
            stop_reason="tool_use",
        ))
        _, args, _ = mock_dispatch.call_args.args
        assert args["x"] == 1024
        assert args["y"] == 768


def test_loop_does_not_scale_at_scale_1():
    from unittest.mock import patch
    from agent.loop import AgentLoop
    mock_backend = MagicMock(spec=BackendAdapter)
    loop = AgentLoop({"loop": {"confirm_destructive_actions": False}}, mock_backend)
    loop._scale_factor = 1.0
    with patch("agent.loop._dispatch_tool", return_value="OK") as mock_dispatch:
        loop._act(AgentResponse(
            content="",
            tool_calls=[{"name": "mouse_move", "input": {"x": 512, "y": 384}, "id": "m1"}],
            stop_reason="tool_use",
        ))
        _, args, _ = mock_dispatch.call_args.args
        assert args["x"] == 512
        assert args["y"] == 384


def test_loop_scales_drag_coordinates():
    from unittest.mock import patch
    from agent.loop import AgentLoop
    mock_backend = MagicMock(spec=BackendAdapter)
    loop = AgentLoop({"loop": {"confirm_destructive_actions": False}}, mock_backend)
    loop._scale_factor = 1.5
    with patch("agent.loop._dispatch_tool", return_value="OK") as mock_dispatch:
        loop._act(AgentResponse(
            content="",
            tool_calls=[{"name": "mouse_drag",
                         "input": {"from_x": 100, "from_y": 200,
                                   "to_x": 300, "to_y": 400}, "id": "d1"}],
            stop_reason="tool_use",
        ))
        _, args, _ = mock_dispatch.call_args.args
        assert args["from_x"] == 150
        assert args["from_y"] == 300
        assert args["to_x"] == 450
        assert args["to_y"] == 600


# ── Non-vision model support ─────────────────────────────────────────────────

def test_non_vision_backend_skips_images():
    """A backend without vision gets no images in send_message."""
    mock_backend = MagicMock(spec=BackendAdapter)
    mock_backend.supports_vision.return_value = False
    mock_backend.send_message.return_value = AgentResponse(
        content="done", tool_calls=[], stop_reason="end_turn",
    )
    loop = AgentLoop(_MOCK_CONFIG, mock_backend)
    loop.run("test")
    _, kwargs = mock_backend.send_message.call_args
    assert kwargs["images"] == []


def test_vision_backend_receives_images():
    """A vision backend gets the screenshot in send_message."""
    mock_backend = MagicMock(spec=BackendAdapter)
    mock_backend.supports_vision.return_value = True
    mock_backend.send_message.return_value = AgentResponse(
        content="done", tool_calls=[], stop_reason="end_turn",
    )
    loop = AgentLoop(_MOCK_CONFIG, mock_backend)
    loop.run("test")
    _, kwargs = mock_backend.send_message.call_args
    assert isinstance(kwargs["images"], list)
    assert len(kwargs["images"]) == 1


def test_perceive_disabled_scaling_config():
    """scale_screenshots: false should not alter the screenshot."""
    mock_backend = MagicMock(spec=BackendAdapter)
    loop = AgentLoop(
        {"loop": {"scale_screenshots": False, "confirm_destructive_actions": False}},
        mock_backend,
    )
    loop._scale_screenshots = False
    perception = loop._perceive()
    assert perception["scale"] == 1.0


def test_ollama_non_vision_heuristic():
    from agent.backends.ollama import OllamaBackend
    cfg = {"model": "llama3", "endpoint": "http://localhost:11434"}
    backend = OllamaBackend(cfg)
    assert backend.supports_vision() is False
