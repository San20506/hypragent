"""Ollama backend adapter — Milestone M11."""

import ollama

from agent.backends.base import AgentResponse, BackendAdapter


class OllamaBackend(BackendAdapter):
    """Local Ollama backend (llava or minicpm-v for vision support)."""

    def __init__(self, config: dict) -> None:
        self.config = config
        self._model: str = config["model"]
        self._client = ollama.Client(host=config.get("endpoint", "http://localhost:11434"))

    def send_message(
        self,
        messages: list[dict],
        tools: list[dict],
        images: list[str],
    ) -> AgentResponse:
        # Convert tools to Ollama function format
        ollama_tools = [
            {
                "type": "function",
                "function": {
                    "name": t["name"],
                    "description": t.get("description", ""),
                    "parameters": t.get("inputSchema", {}),
                },
            }
            for t in tools
        ] if tools else None

        # Build messages, flattening any list content to text
        api_messages = []
        for msg in messages:
            role = msg["role"]
            content = msg["content"]
            if isinstance(content, list):
                text = " ".join(
                    b.get("text", "") or b.get("content", "")
                    for b in content if isinstance(b, dict)
                )
                api_messages.append({"role": role, "content": text})
            else:
                api_messages.append({"role": role, "content": content})

        # Inject screenshots into last user message
        if images and api_messages:
            api_messages[-1]["images"] = images

        response = self._client.chat(
            model=self._model,
            messages=api_messages,
            tools=ollama_tools,
        )

        msg = response.message
        content = msg.content or ""
        tool_calls: list[dict] = []
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            for i, tc in enumerate(msg.tool_calls):
                tool_calls.append({
                    "name": tc.function.name,
                    "input": dict(tc.function.arguments),
                    "id": f"ollama_{i}",
                })

        stop_reason = "end_turn" if not tool_calls else "tool_use"
        return AgentResponse(content=content, tool_calls=tool_calls, stop_reason=stop_reason)

    def get_model_name(self) -> str:
        return self._model

    def supports_vision(self) -> bool:
        # Vision models: llava, minicpm-v, bakllava — heuristic
        return any(v in self._model.lower() for v in ("llava", "minicpm", "bakllava", "vision"))
