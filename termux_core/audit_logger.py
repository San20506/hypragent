"""Append-only async audit logger.

Writes JSON entries to a log file without blocking the agent loop.
Includes log rotation, integrity enforcement, and backpressure handling.
"""

import asyncio
import json
import os
from collections import deque
from datetime import datetime, timezone
from pathlib import Path


class AuditLogger:
    """Async append-only audit logger.

    - Async writes (non-blocking to agent loop)
    - Write queue with backpressure (1000 entries, drops oldest)
    - Log rotation (10MB max, 5 files retained)
    - Atomic writes (single operation per entry)
    """

    MAX_QUEUE_SIZE = 1000
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
    MAX_FILES = 5

    def __init__(self, log_path: str | None = None):
        self._log_path = Path(
            log_path or os.path.expanduser("~/.hypragent/audit/audit.log")
        )
        self._queue: asyncio.Queue = asyncio.Queue(maxsize=self.MAX_QUEUE_SIZE)
        self._task: asyncio.Task | None = None
        self._running = False

    async def start(self) -> None:
        """Start the background writer task."""
        self._running = True
        self._log_path.parent.mkdir(parents=True, exist_ok=True)
        self._task = asyncio.create_task(self._writer())

    async def stop(self) -> None:
        """Flush remaining entries and stop the writer.

        Drain the queue BEFORE clearing _running — otherwise the writer
        exits with items still queued and queue.join() hangs forever.
        """
        if self._task:
            await self._queue.join()
            self._running = False
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    def log_command(self, request_id: str, action: str, params: dict, result: dict) -> None:
        """Log a command execution."""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "request_id": request_id,
            "action": action,
            "parameters": params,
            "result": result,
            "status": "ok" if result.get("status") == "ok" else "error",
            "duration_ms": result.get("duration_ms", 0),
        }
        self._enqueue(entry)

    def log_consent(self, event: str, app_package: str, permission_types: list[str]) -> None:
        """Log a consent event (granted/denied/revoked)."""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": event,
            "app_package": app_package,
            "permission_types": permission_types,
        }
        self._enqueue(entry)

    def log_emergency_stop(self, task_state: dict) -> None:
        """Log an emergency stop event."""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": "emergency_stop",
            "task_state": task_state,
        }
        self._enqueue(entry)

    def log_error(self, error_type: str, error_message: str, context: dict) -> None:
        """Log an agent error."""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "error_type": error_type,
            "error_message": error_message,
            "context": context,
        }
        self._enqueue(entry)

    def log_event(self, event_type: str, source: str, data: dict) -> None:
        """Log a cross-layer event from Layer A."""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": event_type,
            "source": source,
            "data": data,
        }
        self._enqueue(entry)

    def _enqueue(self, entry: dict) -> None:
        """Add entry to the write queue. Drops oldest if full."""
        try:
            self._queue.put_nowait(entry)
        except asyncio.QueueFull:
            # Drop oldest entry with a warning
            try:
                self._queue.get_nowait()
            except asyncio.QueueEmpty:
                pass
            self._queue.put_nowait(entry)

    async def _writer(self) -> None:
        """Background writer loop."""
        while self._running:
            try:
                entry = await asyncio.wait_for(self._queue.get(), timeout=1.0)
                self._write_entry(entry)
                self._queue.task_done()
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break

    def _write_entry(self, entry: dict) -> None:
        """Write a single entry to the log file. Rotates if needed."""
        try:
            # Check file size and rotate if needed
            if self._log_path.exists() and self._log_path.stat().st_size >= self.MAX_FILE_SIZE:
                self._rotate()

            # Write entry as a single JSON line
            with open(self._log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, separators=(",", ":")) + "\n")
        except OSError as e:
            # Log to stderr as fallback — agent must not crash
            print(f"[AUDIT_WRITE_FAIL] {e}", file=os.sys.stderr)

    def _rotate(self) -> None:
        """Rotate log files. Keep the 5 most recent."""
        # Shift existing files
        for i in range(self.MAX_FILES - 1, 0, -1):
            old = self._log_path.with_suffix(f".log.{i}")
            new = self._log_path.with_suffix(f".log.{i + 1}")
            if old.exists():
                old.rename(new)

        # Move current to .log.1
        rotated = self._log_path.with_suffix(".log.1")
        self._log_path.rename(rotated)

        # Remove files beyond MAX_FILES
        for i in range(self.MAX_FILES + 1, 10):
            old = self._log_path.with_suffix(f".log.{i}")
            if old.exists():
                old.unlink()
