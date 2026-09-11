"""File management tool — Milestone M8.

Safety: All file operations are sandboxed to a configurable directory.
Paths are resolved to absolute and validated to stay within the sandbox.
Symlinks pointing outside the sandbox are rejected.
"""

import os
import shutil
from pathlib import Path


# Default sandbox directory — can be overridden via config
_DEFAULT_SANDBOX_DIR = os.path.expanduser("~/.hypragent/workspace")
_sandbox_dir: str | None = None


def set_sandbox_dir(path: str) -> None:
    """Set the sandbox directory for file operations.

    Args:
        path: Absolute path to the sandbox directory.
    """
    global _sandbox_dir
    _sandbox_dir = os.path.abspath(path)
    os.makedirs(_sandbox_dir, exist_ok=True)


def get_sandbox_dir() -> str:
    """Get the current sandbox directory."""
    if _sandbox_dir is None:
        set_sandbox_dir(_DEFAULT_SANDBOX_DIR)
    return _sandbox_dir


def _validate_path(path: str) -> str:
    """Validate that a path is within the sandbox directory.

    Args:
        path: Path to validate (absolute or relative).

    Returns:
        Resolved absolute path.

    Raises:
        ValueError: If path is outside the sandbox or is a symlink escaping it.
    """
    sandbox = get_sandbox_dir()

    # Resolve to absolute path
    if not os.path.isabs(path):
        path = os.path.join(sandbox, path)

    resolved = os.path.realpath(path)

    # Check that resolved path starts with sandbox
    if not resolved.startswith(os.path.realpath(sandbox) + os.sep) and resolved != os.path.realpath(sandbox):
        raise ValueError(
            f"Path {path!r} is outside the sandbox directory {sandbox!r}. "
            f"All file operations must stay within the sandbox."
        )

    # If path exists, check it's not a symlink pointing outside
    if os.path.islink(path):
        link_target = os.path.realpath(path)
        if not link_target.startswith(os.path.realpath(sandbox) + os.sep):
            raise ValueError(
                f"Symlink {path!r} points outside the sandbox to {link_target!r}."
            )

    return resolved


def file_list(path: str) -> list[dict]:
    """List directory contents.

    Args:
        path: Directory path (absolute or relative to sandbox).

    Returns:
        List of dicts with keys: name, path, is_dir, size, modified.
    """
    validated = _validate_path(path)
    entries = []
    with os.scandir(validated) as it:
        for entry in it:
            stat = entry.stat(follow_symlinks=False)
            entries.append({
                "name": entry.name,
                "path": entry.path,
                "is_dir": entry.is_dir(follow_symlinks=False),
                "size": stat.st_size,
                "modified": stat.st_mtime,
            })
    return entries


def file_read(path: str) -> str:
    """Read a text file and return its contents.

    Args:
        path: File path (absolute or relative to sandbox).

    Returns:
        File contents as string (UTF-8 decoded).
    """
    validated = _validate_path(path)
    with open(validated, encoding="utf-8") as f:
        return f.read()


def file_write(path: str, content: str) -> None:
    """Write content to a file.

    Args:
        path: File path (absolute or relative to sandbox).
        content: Content to write.
    """
    validated = _validate_path(path)
    # Ensure parent directory exists
    os.makedirs(os.path.dirname(validated), exist_ok=True)
    with open(validated, "w", encoding="utf-8") as f:
        f.write(content)


def file_move(src: str, dst: str) -> None:
    """Move or rename a file.

    Args:
        src: Source path (absolute or relative to sandbox).
        dst: Destination path (absolute or relative to sandbox).
    """
    validated_src = _validate_path(src)
    validated_dst = _validate_path(dst)
    shutil.move(validated_src, validated_dst)


def file_delete(path: str) -> None:
    """Delete a file.

    Args:
        path: File path (absolute or relative to sandbox).
    """
    validated = _validate_path(path)
    os.remove(validated)
