"""Example: use individual tools without the agent loop.

Demonstrates screenshot, OCR, terminal, and file operations.
Requires a running Wayland session with ydotoold for mouse/keyboard examples.
"""

import os
import tempfile
import base64

# ── Screenshot ────────────────────────────────────────────────────────────────

from tools.screenshot import capture_fullscreen, capture_region

print("Taking fullscreen screenshot...")
b64 = capture_fullscreen()
print(f"  Got {len(b64)} base64 chars")

# Save to file
with open("/tmp/hypr-screenshot.png", "wb") as f:
    f.write(base64.b64decode(b64))
print("  Saved to /tmp/hypr-screenshot.png")

# ── OCR ───────────────────────────────────────────────────────────────────────

from tools.ocr import extract_text_fullscreen

print("\nExtracting screen text via OCR...")
text = extract_text_fullscreen()
preview = text[:200].replace("\n", " ")
print(f"  First 200 chars: {preview!r}")

# ── Terminal ──────────────────────────────────────────────────────────────────

from tools.terminal import terminal_run

print("\nRunning terminal command...")
result = terminal_run("echo 'HyprAgent demo' && uname -r")
print(f"  Exit code: {result.returncode}")
print(f"  Output: {result.stdout.strip()!r}")

# ── File operations ───────────────────────────────────────────────────────────

from tools.files import file_write, file_read, file_delete

print("\nFile operations...")
path = "/tmp/hypr-demo.txt"
file_write(path, "Hello from HyprAgent!", confirm=False)
content = file_read(path)
print(f"  Wrote and read: {content!r}")
file_delete(path, confirm=False)
print(f"  Deleted {path}")

print("\nDone.")
