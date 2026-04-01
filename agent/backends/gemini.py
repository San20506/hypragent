"""Gemini backend adapter. Implemented in Milestone M11."""

from agent.backends.base import AgentResponse, BackendAdapter


class GeminiBackend(BackendAdapter):
    """Google Gemini backend (gemini-2.5-flash default)."""

    def __init__(self, config: dict) -> None:
        self.config = config
        # TODO M11: Initialize google.generativeai client

    def send_message(
        self,
        messages: list[dict],
        tools: list[dict],
        images: list[str],
    ) -> AgentResponse:
        # TODO M11: Implement Gemini API call with vision support
        raise NotImplementedError("M11: GeminiBackend.send_message not yet implemented")

    def get_model_name(self) -> str:
        raise NotImplementedError("M11: GeminiBackend.get_model_name not yet implemented")

    def supports_vision(self) -> bool:
        return True
