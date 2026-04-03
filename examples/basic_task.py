"""Basic example: run a single agent task.

This script demonstrates the simplest way to use HyprAgent.
The agent will perceive the screen, reason about the task, and act.

Usage:
    1. Export your API key:
       export ANTHROPIC_API_KEY=sk-ant-...

    2. Copy the config:
       cp config.yaml.example config.yaml

    3. Run the example:
       uv run python examples/basic_task.py
"""

import sys
import yaml
from agent.backends import load_backend
from agent.loop import AgentLoop


def main() -> None:
    with open("config.yaml") as f:
        config = yaml.safe_load(f)

    try:
        backend = load_backend(config)
    except Exception as e:
        print(f"Failed to load backend: {e}", file=sys.stderr)
        sys.exit(1)

    loop = AgentLoop(config, backend)

    print("Starting agent task: Take a screenshot and describe what's on screen")
    print("Press Ctrl+C to stop early\n")

    try:
        loop.run("Take a screenshot and describe what's on screen in one sentence.")
        print("\nTask completed successfully!")
    except KeyboardInterrupt:
        print("\nTask interrupted by user.")
    except Exception as e:
        print(f"Error during task: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
