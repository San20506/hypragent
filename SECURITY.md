# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 1.0.x   | Yes       |
| < 1.0   | No        |

---

## Reporting a Vulnerability

**Do not open a public GitHub issue for security vulnerabilities.**

To report a vulnerability:

1. Email the maintainers directly, or
2. Use [GitHub's private security advisory](../../security/advisories/new) feature.

Include:
- A description of the vulnerability and its potential impact
- Steps to reproduce or a proof-of-concept (if available)
- Any suggested mitigations

You will receive an acknowledgment within 72 hours. We aim to release a fix within 14 days for critical issues.

---

## Security Model

HyprAgent runs **without sandboxing** on a live Wayland desktop. Understand the implications:

### What HyprAgent can do

- Capture full screen content (including passwords, sensitive data)
- Move the mouse and type arbitrary text into any focused window
- Execute shell commands (subject to the blocklist)
- Read, write, move, and delete files accessible to your user
- Control browser sessions including navigation and form input

### Mitigations built in

| Control | Description |
|---------|-------------|
| **Kill switch** | Ctrl+C (always) or configurable hotkey stops the agent immediately |
| **Audit log** | Every tool call logged to `~/.config/hypr-agent/audit.log` |
| **Destructive confirmation** | File write/move/delete prompt by default (`confirm_destructive_actions: true`) |
| **Command blocklist** | `rm -rf /`, `dd if=`, `mkfs`, fork bomb blocked unconditionally |
| **Timeout** | `terminal_run` enforces a timeout (default 30s) |
| **No sudo** | No tool requires or requests elevated privileges |

### Recommendations

- Run with `confirm_destructive_actions: true` (default).
- Review the audit log regularly: `tail -f ~/.config/hypr-agent/audit.log | python3 -m json.tool`
- Do not expose the MCP server port over a network without authentication.
- Keep API keys in environment variables only — never in `config.yaml`.
- Use `loop.max_steps` to limit autonomous operation length.

---

## Credentials

- API keys are read from environment variables at runtime.
- `config.yaml` must never contain credentials (use `api_key_env` to name the variable).
- `.env` and `config.yaml` are in `.gitignore` — never commit them.
