"""Terminal command execution tool — Milestone M9.

Safety: Commands are run via subprocess list args (no shell=True).
Blocklist and timeout enforced per config.
"""

import shlex
import subprocess
from dataclasses import dataclass


@dataclass
class TerminalResult:
    """Structured output from a terminal command."""
    stdout: str
    stderr: str
    returncode: int
    timed_out: bool


# Matches config.yaml.example safety.command_blocklist — config-driven binding in M13
BLOCKLIST = [
    "rm -rf /",
    "dd if=",
    "mkfs",
    ":(){:|:&};:",
]


def terminal_run(
    command: str,
    cwd: str | None = None,
    timeout: int = 30,
) -> TerminalResult:
    """Run a shell command and return structured output.

    Args:
        command: Shell command string to execute.
        cwd: Working directory for the command (defaults to project root).
        timeout: Maximum seconds to wait before killing the process.

    Returns:
        TerminalResult with stdout, stderr, returncode, timed_out.

    Raises:
        ValueError: If command matches a blocklist entry.
    """
    for blocked in BLOCKLIST:
        if blocked in command:
            raise ValueError(f"Command blocked by safety policy: {blocked!r}")

    args = shlex.split(command)
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


def terminal_run_interactive(command: str) -> None:
    """Open a command in the user's terminal emulator.

    Use for commands that require interactive input (e.g. text editors, REPLs).
    The terminal window is opened but not monitored.

    Args:
        command: Shell command to run interactively.
    """
    # TODO M9: Detect terminal emulator (foot, kitty, alacritty) from env and open
    raise NotImplementedError("M9: terminal_run_interactive not yet implemented")
