"""Claude backend adapter. Implemented in Milestone M4."""

from agent.backends.base import AgentResponse, BackendAdapter


class ClaudeBackend(BackendAdapter):
    """Anthropic Claude backend (claude-sonnet-4-6 default)."""

    def __init__(self, config: dict) -> None:
        self.config = config
        # TODO M4: Initialize anthropic.Anthropic client

    def send_message(
        self,
        messages: list[dict],
        tools: list[dict],
        images: list[str],
    ) -> AgentResponse:
        # TODO M4: Implement Claude API call with vision support
        raise NotImplementedError("M4: ClaudeBackend.send_message not yet implemented")

    def get_model_name(self) -> str:
        # TODO M4: Return from config
        raise NotImplementedError("M4: ClaudeBackend.get_model_name not yet implemented")

    def supports_vision(self) -> bool:
        return True
