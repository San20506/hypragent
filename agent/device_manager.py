"""DEPRECATED — Device manager merged into harness.

This file remains for backward compatibility. All platform-specific
device logic now lives in harness/hyprland.py.
Import from harness instead:

    from harness import detect_harness
    h = detect_harness()
    h.start()
"""

from harness import detect_harness

_devices = None


def _get_devices():
    global _devices
    if _devices is None:
        _devices = detect_harness()
        _devices.start()
    return _devices


class _DeviceRedirect:
    """Thin compatibility shim — delegates to active harness."""

    def start(self, config=None):
        _get_devices().start(config)

    def stop(self):
        if _devices is not None:
            _devices.stop()

    def verify(self):
        return _get_devices().verify()

    @property
    def keyboard(self):
        return _get_devices().keyboard

    @property
    def mouse(self):
        return _get_devices().mouse


devices = _DeviceRedirect()
