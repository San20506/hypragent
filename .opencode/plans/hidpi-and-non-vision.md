# HiDPI Scaling + Non-Vision Model Support — Integration Plan

## Scope

Two integrated features:
1. **HiDPI-aware screenshot scaling** — scale screenshots down for token efficiency, scale model-returned coordinates back up to native pixels.
2. **Non-vision model support** — when the backend doesn't support vision, skip sending screenshots and rely solely on OCR text for perception.

## Current State (Problems)

### Problem 1: No HiDPI scaling
- `capture_fullscreen()` returns native-resolution base64 PNG (e.g., 3840x2160 on 4K)
- Every loop iteration sends a huge image to the model, burning tokens
- Claude Computer Use scales to XGA (1024x768) and maps coordinates back
- HyprAgent has no coordinate scaling at all

### Problem 2: No non-vision model support
- `agent/loop.py` unconditionally passes `images=[screenshot_b64]` to `send_message()`
- `backend.supports_vision()` exists in the ABC but is **never called** by the loop
- Ollama models without vision (e.g., `llama3`, `mistral`) get screenshots they can't process
- The loop should fall back to OCR-only perception for non-vision backends

## Architecture

### Design Principle
Scale in the agent loop, not in the harness. The harness captures at native resolution; the loop scales before sending to the model. This avoids protocol changes and works with all harnesses immediately.

Coordinate scaling happens in `_act()` — before dispatching tool calls, mouse coordinates are divided by the scale factor to convert from model-space back to native screen-space.

### Data Flow (After Changes)

```
AgentLoop.run()
  └─ _perceive()
       ├─ capture_fullscreen() → native base64 PNG
       ├─ extract_text_fullscreen() → OCR text
       └─ Returns: {"screenshot_b64": ..., "ocr_text": ..., "scale": 1.0}

  └─ _reason(perception, task)
       ├─ If backend.supports_vision():
       │    send images=[perception["screenshot_b64"]]
       │    system_prompt includes "You can see the screen"
       └─ If NOT supports_vision():
            send NO images
            system_prompt includes "You perceive the screen through OCR text only"

  └─ _act(response)
       ├─ For each tool_call with coordinates:
       │    scale coordinates: native_x = model_x * scale_factor
       │    scale coordinates: native_y = model_y * scale_factor
       └─ dispatch_tool(scaled_args)
```

## Implementation

### Phase 1: Screenshot Scaling Utility (~30 lines)

Add a `scale_screenshot` function in `agent/loop.py` (or a new `agent/scaling.py`):

```python
def scale_screenshot(base64_png: str, max_w: int = 1024, max_h: int = 768):
    """Scale a base64 PNG down to fit within max_w x max_h.

    Returns:
        (scaled_base64, scale_factor) where scale_factor = native_w / scaled_w
    """
    import base64, io
    from PIL import Image

    data = base64.b64decode(base64_png)
    img = Image.open(io.BytesIO(data))
    orig_w, orig_h = img.size

    if orig_w <= max_w and orig_h <= max_h:
        return base64_png, 1.0  # No scaling needed

    ratio = min(max_w / orig_w, max_h / orig_h)
    new_w = int(orig_w * ratio)
    new_h = int(orig_h * ratio)
    img = img.resize((new_w, new_h), Image.LANCZOS)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii"), 1.0 / ratio
```

### Phase 2: Agent Loop Changes (~60 lines)

#### 2.1 `_perceive()` — track scale factor

```python
def _perceive(self) -> dict:
    screenshot = capture_fullscreen()
    ocr_text = ""
    try:
        ocr_text = extract_text_fullscreen()
    except Exception:
        pass

    scale = 1.0
    if self._scale_screenshots:
        screenshot, scale = scale_screenshot(screenshot)

    return {
        "screenshot_b64": screenshot,
        "ocr_text": ocr_text,
        "scale": scale,
    }
```

#### 2.2 `_reason()` — conditional image sending

```python
def _reason(self, perception: dict, task: str) -> AgentResponse:
    ocr_text = perception["ocr_text"].strip()
    scale = perception.get("scale", 1.0)

    if self.backend.supports_vision():
        images = [perception["screenshot_b64"]]
        vision_note = "You can see the screen via screenshots."
    else:
        images = []
        vision_note = "You cannot see the screen. Perceive through OCR text only."

    if not self._history:
        content = (
            f"{_SYSTEM_PROMPT}\n\n"
            f"Screen resolution: {self._screen_w}x{self._screen_h} "
            f"(scale factor: {scale:.2f}x)\n\n"
            f"{vision_note}\n\n"
            f"Task: {task}\n\n"
            f"Screen OCR:\n{ocr_text}"
        )
    else:
        content = (
            f"Screen OCR:\n{ocr_text}\n"
            f"(Scale factor: {scale:.2f}x — coordinates are in native screen pixels)"
        )

    messages = [*self._history, {"role": "user", "content": content}]

    return self.backend.send_message(
        messages=messages,
        tools=AGENT_TOOLS,
        images=images,
    )
```

#### 2.3 `_act()` — scale coordinates back up

```python
def _act(self, response: AgentResponse) -> list[dict]:
    results = []
    scale = self._scale_factor  # set by _perceive()

    for tc in response.tool_calls:
        args = dict(tc["input"])
        # Scale mouse coordinates from model-space back to native pixels
        if tc["name"] in MOUSE_COORD_TOOLS:
            if "x" in args and "y" in args:
                args["x"] = int(args["x"] * scale)
                args["y"] = int(args["y"] * scale)
            if "from_x" in args and "from_y" in args:
                args["from_x"] = int(args["from_x"] * scale)
                args["from_y"] = int(args["from_y"] * scale)
                args["to_x"] = int(args["to_x"] * scale)
                args["to_y"] = int(args["to_y"] * scale)

        result_str = _dispatch_tool(tc["name"], args)
        _audit(tc["name"], args, result_str)
        results.append({
            "type": "tool_result",
            "tool_use_id": tc["id"],
            "content": result_str,
        })
    return results
```

Where `MOUSE_COORD_TOOLS` is a frozenset:
```python
MOUSE_COORD_TOOLS = frozenset({
    "mouse_move", "mouse_click", "mouse_drag", "mouse_scroll",
    "windows_workspace_switch",  # virtual desktop switching uses coordinates conceptually
})
```

#### 2.4 `__init__()` — new config

```python
def __init__(self, config: dict, backend: BackendAdapter) -> None:
    self.config = config
    self.backend = backend
    self._step = 0
    self._history: list[dict] = []
    self._killed = False
    self._scale_factor = 1.0
    self._scale_screenshots = config.get("loop", {}).get("scale_screenshots", True)
    # Get screen resolution from harness for the system prompt
    from tools import _get_harness
    h = _get_harness()
    self._screen_w, self._screen_h = h.screen_resolution()
    os.makedirs(os.path.dirname(_AUDIT_LOG), exist_ok=True)
    signal.signal(signal.SIGINT, self._handle_sigint)
```

### Phase 3: Config Schema Update

Add to `config.yaml.example` and `_load_config()` defaults:

```yaml
loop:
  max_steps: 20
  confirm_destructive_actions: true
  scale_screenshots: true       # NEW: scale screenshots for HiDPI/token efficiency
  scale_max_width: 1024         # NEW: max width for scaled screenshots
  scale_max_height: 768         # NEW: max height for scaled screenshots
```

### Phase 4: System Prompt Update

Update `_SYSTEM_PROMPT` to mention:
- The agent perceives the screen through screenshots (if vision) or OCR text (if no vision)
- Coordinate system: all coordinates are in native screen pixels
- The scale factor is provided so the agent knows the relationship

### Phase 5: Backend `supports_vision()` Fixes

The `OllamaBackend.supports_vision()` heuristic is already reasonable. But `ClaudeBackend` and `OpenAICompatibleBackend` always return `True`. This is fine — they do support vision.

No changes needed to backends. The loop now respects the return value.

### Phase 6: Tests

Add tests for:
1. `scale_screenshot()` — no-op for small images, scales down for large images, returns correct scale factor
2. Agent loop with vision backend — sends images
3. Agent loop with non-vision backend — skips images, uses OCR only
4. Coordinate scaling in `_act()` — mouse_move(512, 384) at scale=2.0 → harness receives (1024, 768)
5. Config `scale_screenshots: false` — no scaling applied

## File Changes

| File | Change | Lines |
|------|--------|-------|
| `agent/loop.py` | Add scaling utility, modify `_perceive()`, `_reason()`, `_act()`, `__init__()` | ~80 |
| `config.yaml.example` | Add `scale_screenshots`, `scale_max_width`, `scale_max_height` | ~5 |
| `mcp_server.py` | Update `_load_config()` defaults for new config keys | ~3 |
| `tests/test_integration.py` | Add scaling and non-vision tests | ~40 |

**Total: ~130 lines changed across 4 files.**

## Key Design Decisions

1. **Scale in the loop, not the harness** — avoids protocol changes, works with all harnesses, keeps harness simple.
2. **Scale factor stored on the loop instance** — `_act()` reads it directly, no need to pass it through dispatch.
3. **`supports_vision()` check in `_reason()`** — clean separation: perception captures everything, reasoning decides what to send.
4. **OCR text always sent** — even with vision models, OCR provides a text channel that's cheaper than image tokens for reading UI text.
5. **No new dependencies** — PIL/Pillow is already a dependency, `Image.resize()` with `LANCZOS` is stdlib-quality.

## Verification

1. `uv run pytest tests/ -m "not wayland" -v` — all existing tests still pass
2. `python -c "from agent.loop import scale_screenshot; ..."` — scaling utility works
3. Agent loop with Ollama non-vision model — no images sent, OCR text used
4. Agent loop with Claude vision model — images sent, coordinates scaled correctly
5. `scale_screenshots: false` in config — no scaling, native resolution sent
6. Mouse click at (512, 384) with scale=2.0 → harness receives (1024, 768)
