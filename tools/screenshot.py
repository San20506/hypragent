"""Screenshot capture tool. Implemented in Milestone M1.

System dependency: grim (pacman -S grim slurp)
"""


def capture_fullscreen() -> str:
    """Capture the entire screen and return as base64-encoded PNG string.

    Returns:
        Base64-encoded PNG string suitable for passing to AI backend.
    """
    # TODO M1: Implement using grim subprocess
    raise NotImplementedError("M1: capture_fullscreen not yet implemented")


def capture_region(x: int, y: int, width: int, height: int) -> str:
    """Capture a screen region and return as base64-encoded PNG string.

    Args:
        x: Left edge of region in screen pixels.
        y: Top edge of region in screen pixels.
        width: Width of region in pixels.
        height: Height of region in pixels.

    Returns:
        Base64-encoded PNG string.
    """
    # TODO M1: Implement using grim -g "x,y widthxheight"
    raise NotImplementedError("M1: capture_region not yet implemented")


def save_screenshot(path: str) -> None:
    """Capture fullscreen and save to file.

    Args:
        path: Absolute path where PNG file will be saved.
    """
    # TODO M1: Implement using grim path
    raise NotImplementedError("M1: save_screenshot not yet implemented")
