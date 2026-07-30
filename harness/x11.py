"""X11 harness stub — not yet implemented.

Any capability access fails loudly: start() raises, and every other
Harness method hits AttributeError. The full method checklist lives in
harness/base.py's Protocol.
"""


class X11Harness:
    name = "x11"

    def start(self) -> None:
        raise NotImplementedError("X11 harness not yet implemented")

    def stop(self) -> None:
        pass

    def verify(self) -> dict:
        return {"name": self.name, "started": False, "note": "not implemented"}
