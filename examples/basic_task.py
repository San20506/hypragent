"""Basic example: run a single agent task.

Usage:
    export ANTHROPIC_API_KEY=sk-ant-...
    cp config.yaml.example config.yaml
    uv run python examples/basic_task.py
"""

import yaml
from agent.backends import load_backend
from agent.loop import AgentLoop

# Load config
config = yaml.safe_load(open("config.yaml"))

# Build backend (reads API key from env)
backend = load_backend(config)

# Run agent loop
loop = AgentLoop(config, backend)
loop.run("Take a screenshot and describe what's on screen in one sentence.")
