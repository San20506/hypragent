"""Screenshot capture tool. Milestone M1.

System dependency: grim (pacman -S grim slurp)
"""

import base64
import os
import subprocess
import tempfile
import uuid


def capture_fullscreen() -> str:
    """Capture the entire screen and return as base64-encoded PNG string.

    Returns:
        Base64-encoded PNG string suitable for passing to AI backend.

    Raises:
        RuntimeError: If grim exits non-zero.
    """
    path = os.path.join(tempfile.gettempdir(), f"hypr-screenshot-{uuid.uuid4()}.png")
    try:
        result = subprocess.run(
            ["grim", path],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(f"grim failed: {result.stderr.strip()}")
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode("ascii")
    finally:
        if os.path.exists(path):
            os.remove(path)


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

    path = os.path.join(tempfile.gettempdir(), f"hypr-screenshot-{uuid.uuid4()}.png")
    try:
        result = subprocess.run(
            ["grim", "-g", f"{x},{y} {width}x{height}", path],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(f"grim failed: {result.stderr.strip()}")
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode("ascii")
    finally:
        if os.path.exists(path):
            os.remove(path)


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
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"grim failed: {result.stderr.strip()}")
