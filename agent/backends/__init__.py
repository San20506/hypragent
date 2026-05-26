from agent.backends.base import AgentResponse, BackendAdapter


def load_backend(config: dict) -> BackendAdapter:
    """Instantiate the active backend from full config dict.

    Backends are imported lazily — you only need to install the SDK
    for the backend you actually use.

    Args:
        config: Full config dict (e.g. loaded from config.yaml).
                Uses config["backend"]["active"] to select backend.

    Returns:
        Configured BackendAdapter instance.
    """
    active = config["backend"]["active"]
    match active:
        case "claude":
            from agent.backends.claude import ClaudeBackend
            return ClaudeBackend(config["backend"]["claude"])
        case "gemini":
            from agent.backends.gemini import GeminiBackend
            return GeminiBackend(config["backend"]["gemini"])
        case "ollama":
            from agent.backends.ollama import OllamaBackend
            return OllamaBackend(config["backend"]["ollama"])
        case "openai_compatible" | "openai":
            from agent.backends.openai_compatible import OpenAICompatibleBackend
            return OpenAICompatibleBackend(config["backend"]["openai_compatible"])
        case _:
            raise ValueError(
                f"Unknown backend: {active!r}. "
                f"Must be claude, gemini, ollama, or openai_compatible"
            )


__all__ = [
    "AgentResponse", "BackendAdapter",
    "load_backend",
]
