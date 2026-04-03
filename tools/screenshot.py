"""Screenshot capture tool. Milestone M1.

System dependency: grim (pacman -S grim slurp)
"""

import base64
import subprocess


def _capture(*grim_args: str) -> str:
    """Run grim with output to stdout and return base64-encoded PNG.

    Args:
        *grim_args: Additional arguments inserted before the output path ("-").

    Returns:
        Base64-encoded PNG string suitable for passing to AI backend.

    Raises:
        RuntimeError: If grim exits non-zero.
    """
    result = subprocess.run(
        ["grim", *grim_args, "-"],
        capture_output=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"grim failed: {result.stderr.decode().strip()}")
    return base64.b64encode(result.stdout).decode("ascii")


def capture_fullscreen() -> str:
    """Capture the entire screen and return as base64-encoded PNG string.

    Returns:
        Base64-encoded PNG string suitable for passing to AI backend.

    Raises:
        RuntimeError: If grim exits non-zero.
    """
    return _capture()


def capture_region(x: int, y: int, width: int, height: int) -> str:
    """Capture a screen region and return as base64-encoded PNG string.

    Args:
        x: Left edge of region in screen pixels.
        y: Top edge of region in screen pixels.
        width: Width of region in pixels.
        height: Height of region in pixels.

    Returns:
        Base64-encoded PNG string.

    Raises:
        ValueError: If width or height <= 0.
        RuntimeError: If grim exits non-zero.
    """
    if width <= 0 or height <= 0:
        raise ValueError(f"width and height must be > 0, got {width}x{height}")
    return _capture("-g", f"{x},{y} {width}x{height}")


def save_screenshot(path: str) -> None:
    """Capture fullscreen and save to file.

    Args:
        path: Absolute path where PNG file will be saved.

    Raises:
        RuntimeError: If grim exits non-zero.
    """
    result = subprocess.run(
        ["grim", path],
        capture_output=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"grim failed: {result.stderr.decode().strip()}")
