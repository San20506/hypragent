from agent.backends.base import AgentResponse, BackendAdapter
from agent.backends.claude import ClaudeBackend
from agent.backends.gemini import GeminiBackend
from agent.backends.ollama import OllamaBackend


def load_backend(config: dict) -> BackendAdapter:
    """Instantiate the active backend from full config dict.

    Args:
        config: Full config dict (e.g. loaded from config.yaml).
                Uses config["backend"]["active"] to select backend.

    Returns:
        Configured BackendAdapter instance.
    """
    active = config["backend"]["active"]
    match active:
        case "claude":
            return ClaudeBackend(config["backend"]["claude"])
        case "gemini":
            return GeminiBackend(config["backend"]["gemini"])
        case "ollama":
            return OllamaBackend(config["backend"]["ollama"])
        case _:
            raise ValueError(
                f"Unknown backend: {active!r}. Must be claude, gemini, or ollama"
            )


__all__ = [
    "AgentResponse", "BackendAdapter",
    "ClaudeBackend", "GeminiBackend", "OllamaBackend",
    "load_backend",
]
