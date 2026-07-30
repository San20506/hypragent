"""Self-check for the Termux core. Run: python3 -m termux_core.selfcheck

Exercises the parts that can run without a device or AI backend:
module imports, tool schema shape, local tool round-trip, audit logger.
Exits non-zero if anything is broken.
"""

import asyncio
import json
import os
import sys
import tempfile


def check_imports() -> None:
    from . import agent_loop, android_tools, audit_logger, mcp_server, websocket_server  # noqa: F401
    from .backends.base import AgentResponse, BackendAdapter  # noqa: F401


def check_tool_schema() -> None:
    from .android_tools import ANDROID_TOOLS, LAYER_A_TOOLS, LOCAL_TOOLS

    assert len(ANDROID_TOOLS) >= 13, f"expected >=13 tools, got {len(ANDROID_TOOLS)}"
    names = {t["name"] for t in ANDROID_TOOLS}
    assert names == LAYER_A_TOOLS | LOCAL_TOOLS, (
        f"schema/dispatch mismatch: {names ^ (LAYER_A_TOOLS | LOCAL_TOOLS)}"
    )
    for tool in ANDROID_TOOLS:
        assert tool["name"] and tool["description"], f"tool missing name/description: {tool}"
        assert tool["inputSchema"]["type"] == "object", f"bad schema: {tool['name']}"


def check_local_tools() -> None:
    from .android_tools import dispatch_android_tool

    async def _roundtrip() -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "selfcheck.txt")
            await dispatch_android_tool("file_write", {"path": path, "content": "ok"})
            content = await dispatch_android_tool("file_read", {"path": path})
            assert content == "ok", f"file round-trip failed: {content!r}"
            listing = json.loads(await dispatch_android_tool("file_list", {"path": tmp}))
            assert any(e["name"] == "selfcheck.txt" for e in listing)
            await dispatch_android_tool("file_delete", {"path": path})
            assert not os.path.exists(path)

            result = json.loads(await dispatch_android_tool("termux_exec", {"command": "echo hi"}))
            assert result["stdout"].strip() == "hi" and result["returncode"] == 0

            err = json.loads(await dispatch_android_tool("nope", {}))
            assert "error" in err

    asyncio.run(_roundtrip())


def check_audit_logger() -> None:
    from .audit_logger import AuditLogger

    async def _smoke() -> None:
        with tempfile.TemporaryDirectory() as tmp:
            log = AuditLogger(log_path=os.path.join(tmp, "audit.log"))
            await log.start()
            log.log_command("r1", "tap", {"x": 1, "y": 2}, {"status": "ok", "request_id": "r1"})
            log.log_event("task_submitted", "layer_a", {"task": "test"})
            log.log_emergency_stop({"step": 3})
            await log.stop()
            with open(log._log_path) as f:
                lines = f.readlines()
            assert len(lines) == 3, f"expected 3 entries, got {len(lines)}"
            for line in lines:
                json.loads(line)  # every line must be valid JSON

    asyncio.run(_smoke())


def check_ws_server_construction() -> None:
    from .websocket_server import WebSocketServer

    server = WebSocketServer(port=19999)
    assert not server.is_connected
    server.mark_stopped()
    server.reset_stopped()


def main() -> int:
    checks = [
        ("imports", check_imports),
        ("tool schema", check_tool_schema),
        ("local tools", check_local_tools),
        ("audit logger", check_audit_logger),
        ("ws server construction", check_ws_server_construction),
    ]
    failed = 0
    for name, fn in checks:
        try:
            fn()
            print(f"PASS {name}")
        except Exception as e:
            failed += 1
            print(f"FAIL {name}: {e}")
    print(f"\n{len(checks) - failed}/{len(checks)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
