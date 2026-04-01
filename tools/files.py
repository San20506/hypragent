"""File management tool. Implemented in Milestone M8.

Destructive operations (write, move, delete) respect config.loop.confirm_destructive_actions.
"""


def file_list(path: str) -> list[dict]:
    """List directory contents.

    Args:
        path: Absolute directory path.

    Returns:
        List of dicts with keys: name, path, is_dir, size, modified.
    """
    # TODO M8: Implement using os.scandir
    raise NotImplementedError("M8: file_list not yet implemented")


def file_read(path: str) -> str:
    """Read a text file and return its contents.

    Args:
        path: Absolute file path.

    Returns:
        File contents as string (UTF-8 decoded).
    """
    # TODO M8: Implement with explicit UTF-8 encoding
    raise NotImplementedError("M8: file_read not yet implemented")


def file_write(path: str, content: str, confirm: bool = True) -> None:
    """Write content to a file.

    Args:
        path: Absolute file path to write.
        content: String content to write.
        confirm: If True and config.confirm_destructive_actions is set, prompt user.
    """
    # TODO M8: Implement with confirmation check
    raise NotImplementedError("M8: file_write not yet implemented")


def file_move(src: str, dst: str, confirm: bool = True) -> None:
    """Move or rename a file.

    Args:
        src: Source path.
        dst: Destination path.
        confirm: If True and config.confirm_destructive_actions is set, prompt user.
    """
    # TODO M8: Implement using shutil.move with confirmation check
    raise NotImplementedError("M8: file_move not yet implemented")


def file_delete(path: str, confirm: bool = True) -> None:
    """Delete a file.

    Args:
        path: Absolute file path to delete.
        confirm: If True and config.confirm_destructive_actions is set, prompt user.
    """
    # TODO M8: Implement with confirmation check — no recursive delete
    raise NotImplementedError("M8: file_delete not yet implemented")


def file_open(path: str) -> None:
    """Open a file with its default application.

    Args:
        path: Absolute file path.
    """
    # TODO M8: Implement using subprocess xdg-open
    raise NotImplementedError("M8: file_open not yet implemented")
