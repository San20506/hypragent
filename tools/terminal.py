"""Terminal command execution tool.

Safety: Commands are validated against an allowlist of safe executables.
Only explicitly allowed commands can run. This prevents arbitrary command
execution via interpreters (python, bash, etc.) or indirect vectors.
"""

import platform
import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass
class TerminalResult:
    """Structured output from a terminal command."""
    stdout: str
    stderr: str
    returncode: int
    timed_out: bool


# Allowed commands — only these executables can run.
# Prefix matches: "ls" allows "ls", "lsblk", etc.
# This is an allowlist, not a denylist — everything else is rejected.
ALLOWED_COMMANDS = {
    # File inspection
    "ls", "cat", "head", "tail", "less", "more", "wc", "file", "stat",
    "find", "locate", "which", "whereis", "type",
    # Text processing
    "grep", "egrep", "fgrep", "sed", "awk", "cut", "sort", "uniq", "tr",
    "tee", "xargs", "paste", "join", "split", "fmt",
    # Directory navigation
    "pwd", "cd", "dirs", "pushd", "popd",
    # File operations (read-only)
    "cp", "mv", "ln", "mkdir", "rmdir", "touch", "chmod", "chown",
    # System info
    "uname", "hostname", "uptime", "date", "cal", "df", "du", "free",
    "ps", "top", "htop", "lsof", "netstat", "ss", "ip", "ping",
    # Archives
    "tar", "gzip", "gunzip", "bzip2", "xz", "zip", "unzip",
    # Misc utilities
    "echo", "printf", "test", "true", "false", "sleep", "seq", "yes",
    "diff", "patch", "basename", "dirname", "realpath", "readlink",
    # Editors (viewers only — nano/vim can edit but are commonly needed)
    "nano", "vim", "vi", "emacs",
    # Version control
    "git",
    # Package managers (read-only queries)
    "pacman", "apt", "dnf", "yum", "brew",
}

# Blocked argument patterns — if these appear as standalone arguments, block.
# Catches "rm -rf /" regardless of spacing, and fork bombs.
BLOCKED_ARG_PATTERNS = [
    "rm -rf /",
    "rm -rf /*",
    ":(){ :|:& };:",
    "/dev/sda",
    "/dev/nvme",
    # Windows-specific
    "reg delete",
    "bcdedit",
]


def _check_allowlist(exe: str) -> None:
    """Raise ValueError if executable is not in the allowlist."""
    if not any(allowed == exe or exe.startswith(allowed) for allowed in ALLOWED_COMMANDS):
        raise ValueError(
            f"Command not in allowlist: {exe!r}. "
            f"Only explicitly allowed commands can run. "
            f"See ALLOWED_COMMANDS in terminal.py for the full list."
        )


def _check_blocked_patterns(normalized: str) -> None:
    """Raise ValueError if command matches a blocked argument pattern."""
    for pattern in BLOCKED_ARG_PATTERNS:
        if pattern in normalized:
            raise ValueError(
                f"Command blocked by safety policy: contains {pattern!r}"
            )


def terminal_run(
    command: str,
    cwd: str | None = None,
    timeout: int = 30,
) -> TerminalResult:
    """Run a shell command and return structured output.

    Safety checks (in order):
      1. On POSIX: parses command with shlex to extract executable name.
      2. On Windows: extracts first token for executable check.
      3. Checks the executable name against ALLOWED_COMMANDS (allowlist).
      4. Checks the full command string against BLOCKED_ARG_PATTERNS.

    Args:
        command: Shell command string to execute.
        cwd: Working directory for the command.
        timeout: Maximum seconds to wait before killing the process.

    Returns:
        TerminalResult with stdout, stderr, returncode, timed_out.

    Raises:
        ValueError: If command is not in allowlist or matches blocked pattern.
    """
    is_windows = platform.system() == "Windows"

    if is_windows:
        # Windows: use the raw command string for blocklist checks
        # and pass to cmd.exe via shell=True.
        normalized = command.strip()
        if not normalized:
            raise ValueError("Command must not be empty")

        # Extract first token for executable check
        first_token = normalized.split()[0] if normalized.split() else ""
        exe = Path(first_token).name.lower()
        # Strip .exe, .bat, .cmd, .ps1 extensions for comparison
        for ext in (".exe", ".bat", ".cmd", ".ps1"):
            if exe.endswith(ext):
                exe = exe[: -len(ext)]
                break

        _check_allowlist(exe)
        _check_blocked_patterns(normalized)

        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return TerminalResult(
                stdout=result.stdout,
                stderr=result.stderr,
                returncode=result.returncode,
                timed_out=False,
            )
        except subprocess.TimeoutExpired:
            return TerminalResult(stdout="", stderr="", returncode=-1, timed_out=True)
    else:
        # POSIX: use shlex for proper parsing
        args = shlex.split(command)
        if not args:
            raise ValueError("Command must not be empty")

        exe = Path(args[0]).name
        _check_allowlist(exe)

        # Rejoin with normalized whitespace for pattern matching
        normalized = " ".join(args)
        _check_blocked_patterns(normalized)

        try:
            result = subprocess.run(
                args,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return TerminalResult(
                stdout=result.stdout,
                stderr=result.stderr,
                returncode=result.returncode,
                timed_out=False,
            )
        except subprocess.TimeoutExpired:
            return TerminalResult(stdout="", stderr="", returncode=-1, timed_out=True)
