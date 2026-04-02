"""OCR / screen text extraction tool — Milestone M3.

System dependency: tesseract + tesseract-data-eng (pacman -S tesseract tesseract-data-eng)
Python dependency: pytesseract, Pillow (both in pyproject.toml dependencies)
"""

import os
import subprocess
import tempfile
import uuid

import pytesseract
from PIL import Image


def extract_text_from_image(image_path: str) -> str:
    """Extract text from an image file using Tesseract OCR.

    Args:
        image_path: Path to PNG or JPEG image file.

    Returns:
        Extracted text string.
    """
    img = Image.open(image_path)
    return pytesseract.image_to_string(img)


def extract_text_fullscreen() -> str:
    """Capture full screen and extract all visible text.

    Returns:
        Extracted text string from full screen.
    """
    path = os.path.join(tempfile.gettempdir(), f"hypr-ocr-{uuid.uuid4()}.png")
    try:
        result = subprocess.run(["grim", path], capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"grim failed: {result.stderr.strip()}")
        return pytesseract.image_to_string(Image.open(path))
    finally:
        if os.path.exists(path):
            os.remove(path)


def extract_text_from_region(x: int, y: int, width: int, height: int) -> str:
    """Capture a screen region and extract text from it.

    Args:
        x: Left edge of region.
        y: Top edge of region.
        width: Region width in pixels.
        height: Region height in pixels.

    Returns:
        Extracted text string.
    """
    if width <= 0 or height <= 0:
        raise ValueError(f"width and height must be > 0, got {width}x{height}")
    path = os.path.join(tempfile.gettempdir(), f"hypr-ocr-{uuid.uuid4()}.png")
    try:
        result = subprocess.run(
            ["grim", "-g", f"{x},{y} {width}x{height}", path],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(f"grim failed: {result.stderr.strip()}")
        return pytesseract.image_to_string(Image.open(path))
    finally:
        if os.path.exists(path):
            os.remove(path)
