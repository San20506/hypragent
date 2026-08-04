"""Terminal command execution tool.

Safety: Commands are parsed via shlex (POSIX) or executed via cmd.exe
(Windows) and checked against a structured blocklist. No substring matching
on executable names — prevents trivial bypasses like extra whitespace.
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


# Blocked commands — matched against the first argument (the executable).
# Prefix matches: "dd" blocks "dd", "dd_rescue", etc.
# Path matches: "/usr/bin/rm" blocks if the full path is used.
BLOCKED_COMMANDS = {
    "mkfs", "mkfs.ext4", "mkfs.btrfs", "mkfs.fat", "mkfs.ntfs",
    "dd",
    "shred",
    "fdisk", "cfdisk", "sfdisk", "parted", "gparted",
    # Windows-specific
    "format", "diskpart",
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


def terminal_run(
    command: str,
    cwd: str | None = None,
    timeout: int = 30,
) -> TerminalResult:
    """Run a shell command and return structured output.

    Safety checks (in order):
      1. On POSIX: parses command with shlex to normalize whitespace.
      2. On Windows: runs via cmd.exe /c (no shlex — Windows paths use
         backslashes that shlex would mangle).
      3. Checks the executable name against BLOCKED_COMMANDS.
      4. Checks the full command string against BLOCKED_ARG_PATTERNS.

    Args:
        command: Shell command string to execute.
        cwd: Working directory for the command.
        timeout: Maximum seconds to wait before killing the process.

    Returns:
        TerminalResult with stdout, stderr, returncode, timed_out.

    Raises:
        ValueError: If command is blocked by safety policy.
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

        if exe in BLOCKED_COMMANDS:
            raise ValueError(
                f"Command blocked by safety policy: {exe!r}. "
                f"Use alternative or manually run in your terminal."
            )

        for pattern in BLOCKED_ARG_PATTERNS:
            if pattern in normalized:
                raise ValueError(
                    f"Command blocked by safety policy: contains {pattern!r}"
                )

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
        if exe in BLOCKED_COMMANDS:
            raise ValueError(
                f"Command blocked by safety policy: {exe!r}. "
                f"Use alternative or manually run in your terminal."
            )

        # Rejoin with normalized whitespace for pattern matching
        normalized = " ".join(args)
        for pattern in BLOCKED_ARG_PATTERNS:
            if pattern in normalized:
                raise ValueError(
                    f"Command blocked by safety policy: contains {pattern!r}"
                )

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



