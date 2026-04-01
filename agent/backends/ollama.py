"""Ollama backend adapter. Implemented in Milestone M11."""

from agent.backends.base import AgentResponse, BackendAdapter


class OllamaBackend(BackendAdapter):
    """Local Ollama backend (llava or minicpm-v for vision support)."""

    def __init__(self, config: dict) -> None:
        self.config = config
        # TODO M11: Initialize ollama client with endpoint from config

    def send_message(
        self,
        messages: list[dict],
        tools: list[dict],
        images: list[str],
    ) -> AgentResponse:
        # TODO M11: Implement Ollama API call
        raise NotImplementedError("M11: OllamaBackend.send_message not yet implemented")

    def get_model_name(self) -> str:
        raise NotImplementedError("M11: OllamaBackend.get_model_name not yet implemented")

    def supports_vision(self) -> bool:
        # TODO M11: Check if loaded model supports vision
        raise NotImplementedError("M11: OllamaBackend.supports_vision not yet implemented")
