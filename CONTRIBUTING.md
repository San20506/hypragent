# Contributing to HyprAgent

Thank you for your interest in contributing.

---

## Reporting Issues

Before opening an issue:
1. Search [existing issues](../../issues) to avoid duplicates.
2. Test on a clean CachyOS/Arch install if possible.
3. Include your Hyprland version, Python version, and ydotool version.

Use the appropriate label: `bug`, `enhancement`, `documentation`, `question`.

---

## Pull Requests

### Branch naming

```
feature/short-description    # new capability
fix/short-description        # bug fix
docs/short-description       # documentation only
refactor/short-description   # internal cleanup
```

### Workflow

1. Fork the repo and create a branch from `main`.
2. Install dev dependencies: `uv sync --extra dev`
3. Make your change. Write or update tests.
4. Run the test suite: `uv run pytest tests/ -m "not wayland" -v`
5. All non-wayland tests must pass before submitting.
6. Submit a pull request against `main`.

### Commit messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
feat(tools): add screenshot region selector
fix(mouse): correct scroll direction on ydotool 1.0.4
docs(readme): add Ollama setup instructions
test(integration): add keyboard type round-trip test
```

Types: `feat`, `fix`, `refactor`, `docs`, `test`, `chore`, `perf`

---

## Coding Standards

- **Python 3.11+** — use type annotations on all function signatures.
- **PEP 8** — format with `black`, lint with `ruff`.
- **No hardcoded secrets** — credentials via environment variables only.
- **No `shell=True`** in subprocess calls — use `shlex.split` + list form.
- **Functions under 50 lines** — extract helpers if needed.
- **No mutation** — return new objects rather than modifying in place.

### Running linters

```bash
uv run black .
uv run ruff check .
```

---

## Adding a New Tool

1. Implement in `tools/<name>.py` — follow the existing module pattern.
2. Register the MCP handler in `mcp_server.py` — add `Tool(...)` to `list_tools()` and a `@server.call_tool()` handler.
3. Add the tool schema to `AGENT_TOOLS` in `agent/loop.py`.
4. Add tests to `tests/test_integration.py` — at minimum: happy path + error case.
5. Document the tool in `docs/API.md`.

---

## Adding a New Backend

1. Create `agent/backends/<name>.py` — subclass `BackendAdapter` from `base.py`.
2. Implement all abstract methods: `send_message`, `get_model_name`, `supports_vision`.
3. Register in `agent/backends/__init__.py` → `load_backend()`.
4. Add config keys to `config.yaml.example`.
5. Add `test_load_backend_<name>()` to `tests/test_integration.py`.

---

## Wayland-specific Testing

Tests that require a live Wayland session must be marked:

```python
@pytest.mark.wayland
def test_my_wayland_feature():
    ...
```

Run wayland-only tests manually in your Hyprland session:

```bash
uv run pytest tests/ -m wayland -v
```

---

## License

By contributing, you agree that your contributions will be licensed under the [MIT License](LICENSE).
