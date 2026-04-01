"""OCR / screen text extraction tool. Implemented in Milestone M3.

System dependency: tesseract + tesseract-data-eng (pacman -S tesseract tesseract-data-eng)
Python dependency: pytesseract, Pillow
"""


def extract_text_from_image(image_path: str) -> str:
    """Extract text from an image file using Tesseract OCR.

    Args:
        image_path: Path to PNG or JPEG image file.

    Returns:
        Extracted text string.
    """
    # TODO M3: Implement using pytesseract.image_to_string
    raise NotImplementedError("M3: extract_text_from_image not yet implemented")


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
    # TODO M3: Capture region via tools.screenshot then OCR
    raise NotImplementedError("M3: extract_text_from_region not yet implemented")


def extract_text_fullscreen() -> str:
    """Capture full screen and extract all visible text.

    Returns:
        Extracted text string from full screen.
    """
    # TODO M3: Capture fullscreen via tools.screenshot then OCR
    raise NotImplementedError("M3: extract_text_fullscreen not yet implemented")
