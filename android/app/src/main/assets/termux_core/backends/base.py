"""BackendAdapter ABC for Termux core."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class AgentResponse:
    """Structured response from an AI backend."""
    content: str
    tool_calls: list[dict] = field(default_factory=list)
    stop_reason: str = "end_turn"


class BackendAdapter(ABC):
    """Abstract base class for all AI backend adapters."""

    @abstractmethod
    def send_message(
        self,
        messages: list[dict],
        tools: list[dict],
        images: list[str],
    ) -> AgentResponse:
        """Send messages to the AI backend and return a structured response."""

    @abstractmethod
    def get_model_name(self) -> str:
        """Return the active model identifier string."""

    @abstractmethod
    def supports_vision(self) -> bool:
        """Return True if this backend can process image inputs."""
