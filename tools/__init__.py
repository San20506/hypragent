"""HyprAgent tool modules. Each tool module is implemented in its corresponding milestone."""

from harness import detect_harness

_harness = None


def _get_harness():
    """Return the started platform harness singleton (lazy)."""
    global _harness
    if _harness is None:
        _harness = detect_harness()
        _harness.start()
    return _harness
