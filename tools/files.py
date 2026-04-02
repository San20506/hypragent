"""File management tool — Milestone M8.

Destructive operations (write, move, delete) accept a confirm parameter
reserved for M10 safety controls. Not enforced in MVP.
"""

import os
import shutil
import subprocess


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


def file_write(path: str, content: str, confirm: bool = True) -> None:
    """Write content to a file.

    Args:
        path: Absolute file path to write.
        content: String content to write.
        confirm: Reserved for M10 destructive action confirmation.
    """
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def file_move(src: str, dst: str, confirm: bool = True) -> None:
    """Move or rename a file.

    Args:
        src: Source path.
        dst: Destination path.
        confirm: Reserved for M10 destructive action confirmation.
    """
    shutil.move(src, dst)


def file_delete(path: str, confirm: bool = True) -> None:
    """Delete a file.

    Args:
        path: Absolute file path to delete.
        confirm: Reserved for M10 destructive action confirmation.
    """
    os.remove(path)


def file_open(path: str) -> None:
    """Open a file with its default application.

    Args:
        path: Absolute file path.
    """
    subprocess.run(["xdg-open", path])
