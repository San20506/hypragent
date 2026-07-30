"""OCR / screen text extraction tool — thin dispatcher to active platform harness."""

from tools import _get_harness


def extract_text_from_image(image_path: str) -> str:
    """Extract text from an image file using Tesseract OCR."""
    return _get_harness().extract_text_from_image(image_path)


def extract_text_fullscreen() -> str:
    """Capture full screen and extract all visible text."""
    return _get_harness().extract_text_fullscreen()


def extract_text_from_region(x: int, y: int, width: int, height: int) -> str:
    """Capture a screen region and extract text from it."""
    return _get_harness().extract_text_from_region(x, y, width, height)
