"""File management tool — Milestone M8."""

import os
import shutil


def file_list(path: str) -> list[dict]:
    """List directory contents.

    Args:
        path: Absolute directory path.

    Returns:
        List of dicts with keys: name, path, is_dir, size, modified.
    """
    entries = []
    with os.scandir(path) as it:
        for entry in it:
            stat = entry.stat()
            entries.append({
                "name": entry.name,
                "path": entry.path,
                "is_dir": entry.is_dir(),
                "size": stat.st_size,
                "modified": stat.st_mtime,
            })
    return entries


def file_read(path: str) -> str:
    """Read a text file and return its contents.

    Args:
        path: Absolute file path.

    Returns:
        File contents as string (UTF-8 decoded).
    """
    with open(path, encoding="utf-8") as f:
        return f.read()


def file_write(path: str, content: str) -> None:
    """Write content to a file."""
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def file_move(src: str, dst: str) -> None:
    """Move or rename a file."""
    shutil.move(src, dst)


def file_delete(path: str) -> None:
    """Delete a file."""
    os.remove(path)



