"""Parallel task executor for desktop actions with dependency resolution.

Implements the task-graph execution model from ARCHITECTURE_PARALLEL.md.
Reduces model round-trips by batching independent actions into a single
execute_plan call with dependency-aware ordering and parallel dispatch.
"""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable

from tools.screenshot import capture_fullscreen
from tools.ocr import extract_text_fullscreen

# ── Tool categories for parallel-safety ───────────────────────────────────

# Read-only tools: safe to run in parallel with anything
_READ_ONLY = {
    "hyprland_workspace_list", "hyprland_clients",
    "hyprland_active_window", "file_read", "file_list",
    "read_screen_text", "browser_get_text",
}

# Compositor commands: safe to parallelize (different windows/workspaces)
_COMPOSITOR = {
    "hyprland_workspace_switch", "hyprland_focus_window",
    "hyprland_focus_window_by_title", "hyprland_launch_app",
    "browser_open", "browser_navigate",
}

# Input tools: MUST be serialized (modify screen state directly)
_INPUT = {
    "mouse_move", "mouse_click", "mouse_drag", "mouse_scroll",
    "keyboard_type", "keyboard_press",
    "browser_click", "browser_type", "browser_scroll",
}

# Perceive tools: capture screen state — must run last in any batch
_PERCEIVE = {
    "take_screenshot", "capture_window", "read_screen_text",
    "extract_active_window_text",
}


class ActionPlan:
    """A plan of action tasks with dependency tracking."""

    def __init__(self, actions: list[dict]) -> None:
        self._actions: dict[str, dict] = {a["id"]: a for a in actions}
        self.completed: dict[str, Any] = {}
        self.failed: dict[str, str] = {}

    # ── dependency resolution ────────────────────────────────────────────

    def ready_tasks(self) -> list[dict]:
        """Return tasks whose dependencies are all completed."""
        ready: list[dict] = []
        for tid, task in self._actions.items():
            if tid in self.completed or tid in self.failed:
                continue
            deps = task.get("depends_on", [])
            if all(d in self.completed for d in deps):
                ready.append(task)
        return ready

    def is_done(self) -> bool:
        """True when every task has been completed *or* failed."""
        return len(self.completed) + len(self.failed) >= len(self._actions)

    # ── state transitions ────────────────────────────────────────────────

    def mark_done(self, task_id: str, result: Any) -> None:
        """Record a successful task result."""
        self.completed[task_id] = result
        self._actions.pop(task_id, None)

    def mark_failed(self, task_id: str, error: str) -> None:
        """Record a task failure."""
        self.failed[task_id] = error
        self._actions.pop(task_id, None)


# ── executor ─────────────────────────────────────────────────────────────

def _try_dispatch(
    task: dict,
    dispatch_fn: Callable[..., str],
    _max_workers: int = 4,
) -> tuple[str, str]:
    """Execute one task and return (task_id, result_or_error_string)."""
    tid = task["id"]
    try:
        result = dispatch_fn(task["tool"], task["args"])
        return tid, result
    except Exception as exc:
        return tid, f"Error: {exc}"


def execute_plan(
    actions: list[dict],
    dispatch_fn: Callable[..., str],
    *,
    verify: bool = True,
    max_workers: int = 4,
) -> dict:
    """Execute an action plan with dependency-based parallelism.

    Args:
        actions: List of action dicts.  Each must have ``id``, ``tool``,
            ``args`` and may optionally have ``depends_on`` (list of ids).
        dispatch_fn: A callable ``(tool_name: str, args: dict) -> str``
            that executes a single tool and returns its result.
        verify: If True (default), run cross-effect verification after
            all actions complete (one screenshot + OCR pass).
        max_workers: Maximum number of threads for parallel dispatch.

    Returns:
        Dict with keys ``results`` (completed task id → result),
        ``failed`` (failed task id → error), and ``verification``
        (optional screenshot + OCR snapshot).
    """
    plan = ActionPlan(actions)
    max_iterations = len(actions) + 5  # safety limit against deadlocks

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        for _ in range(max_iterations):
            if plan.is_done():
                break

            ready = plan.ready_tasks()
            if not ready:
                # Deadlock: remaining tasks can never become ready
                for tid in list(plan._actions.keys()):
                    plan.mark_failed(tid, "dependency not met (deadlock)")
                break

            # ── split ready tasks by category ────────────────────────────
            parallel_tasks = [
                t for t in ready
                if t["tool"] not in _INPUT and t["tool"] not in _PERCEIVE
            ]
            input_tasks = [t for t in ready if t["tool"] in _INPUT]
            perceive_tasks = [t for t in ready if t["tool"] in _PERCEIVE]

            # ── 1. parallel-safe tasks (read-only + compositor) ──────────
            if parallel_tasks:
                futures = {
                    pool.submit(_try_dispatch, t, dispatch_fn): t
                    for t in parallel_tasks
                }
                for future in as_completed(futures):
                    tid, result = future.result()
                    if result.startswith("Error:"):
                        plan.mark_failed(tid, result)
                    else:
                        plan.mark_done(tid, result)

            # ── 2. input tasks (sequential — order matters) ──────────────
            for task in input_tasks:
                tid, result = _try_dispatch(task, dispatch_fn)
                if result.startswith("Error:"):
                    plan.mark_failed(tid, result)
                else:
                    plan.mark_done(tid, result)

            # ── 3. perceive tasks (last — capture final state) ───────────
            for task in perceive_tasks:
                tid, result = _try_dispatch(task, dispatch_fn)
                if result.startswith("Error:"):
                    plan.mark_failed(tid, result)
                else:
                    plan.mark_done(tid, result)

    # ── cross-effect verification ────────────────────────────────────────
    verification = None
    if verify and (plan.completed or plan.failed):
        try:
            screenshot_b64 = capture_fullscreen()
            ocr_text = extract_text_fullscreen()
            verification = {
                "screenshot_b64": screenshot_b64,
                "ocr_text": ocr_text,
            }
        except Exception as exc:
            verification = {"error": str(exc)}

    return {
        "results": plan.completed,
        "failed": plan.failed,
        "verification": verification,
    }
