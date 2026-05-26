"""macOS harness stub — not yet implemented."""


class MacOSHarness:
    """Stub harness for macOS."""

    name = "macos"

    def start(self) -> None:
        raise NotImplementedError("macOS harness not yet implemented")

    def stop(self) -> None:
        raise NotImplementedError("macOS harness not yet implemented")

    def verify(self) -> dict:
        return {"name": self.name, "started": False, "note": "not implemented"}

    def capture_fullscreen(self) -> str:
        raise NotImplementedError("macOS harness not yet implemented")

    def capture_region(self, x: int, y: int, w: int, h: int) -> str:
        raise NotImplementedError("macOS harness not yet implemented")

    def save_screenshot(self, path: str) -> None:
        raise NotImplementedError("macOS harness not yet implemented")

    def move_mouse(self, x: int, y: int) -> None:
        raise NotImplementedError("macOS harness not yet implemented")

    def click(self, x: int, y: int, button: str = "left") -> None:
        raise NotImplementedError("macOS harness not yet implemented")

    def double_click(self, x: int, y: int) -> None:
        raise NotImplementedError("macOS harness not yet implemented")

    def drag(self, from_x: int, from_y: int, to_x: int, to_y: int) -> None:
        raise NotImplementedError("macOS harness not yet implemented")

    def scroll(self, x: int, y: int, direction: str, amount: int = 3) -> None:
        raise NotImplementedError("macOS harness not yet implemented")

    def type_text(self, text: str) -> None:
        raise NotImplementedError("macOS harness not yet implemented")

    def press_key(self, key: str) -> None:
        raise NotImplementedError("macOS harness not yet implemented")

    def hotkey(self, *keys: str) -> None:
        raise NotImplementedError("macOS harness not yet implemented")

    def extract_text_from_image(self, image_path: str) -> str:
        raise NotImplementedError("macOS harness not yet implemented")

    def extract_text_fullscreen(self) -> str:
        raise NotImplementedError("macOS harness not yet implemented")

    def extract_text_from_region(self, x: int, y: int, width: int, height: int) -> str:
        raise NotImplementedError("macOS harness not yet implemented")

    def workspace_list(self) -> list[dict]:
        raise NotImplementedError("macOS harness not yet implemented")

    def workspace_switch(self, target: str | int) -> None:
        raise NotImplementedError("macOS harness not yet implemented")

    def clients(self) -> list[dict]:
        raise NotImplementedError("macOS harness not yet implemented")

    def active_window(self) -> dict | None:
        raise NotImplementedError("macOS harness not yet implemented")

    def focus_window(self, target: str) -> None:
        raise NotImplementedError("macOS harness not yet implemented")

    def launch_app(self, name: str) -> None:
        raise NotImplementedError("macOS harness not yet implemented")

    def screen_resolution(self) -> tuple[int, int]:
        raise NotImplementedError("macOS harness not yet implemented")
