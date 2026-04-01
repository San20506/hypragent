"""BackendAdapter ABC — defines the interface all AI backends must implement."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class AgentResponse:
    """Structured response from an AI backend."""
    content: str
    tool_calls: list[dict] = field(default_factory=list)
    stop_reason: str = "end_turn"


class BackendAdapter(ABC):
    """Abstract base class for all AI backend adapters.

    Implementations: ClaudeBackend, GeminiBackend, OllamaBackend.
    Selected via config.yaml backend.active field.
    """

    @abstractmethod
    def send_message(
        self,
        messages: list[dict],
        tools: list[dict],
        images: list[str],
    ) -> AgentResponse:
        """Send messages to the AI backend and return a structured response.

        Args:
            messages: Conversation history in OpenAI-compatible format.
            tools: List of MCP tool schemas available to the model.
            images: List of base64-encoded PNG strings (screenshots).

        Returns:
            AgentResponse with content, any tool_calls, and stop_reason.
        """

    @abstractmethod
    def get_model_name(self) -> str:
        """Return the active model identifier string."""

    @abstractmethod
    def supports_vision(self) -> bool:
        """Return True if this backend can process image inputs."""
