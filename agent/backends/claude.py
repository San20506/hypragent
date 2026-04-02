"""Claude backend adapter — Milestone M4."""

import os

import anthropic

from agent.backends.base import AgentResponse, BackendAdapter


class ClaudeBackend(BackendAdapter):
    """Anthropic Claude backend (claude-sonnet-4-6 default)."""

    def __init__(self, config: dict) -> None:
        self.config = config
        self._model: str = config["model"]
        api_key = os.environ[config["api_key_env"]]
        self._client = anthropic.Anthropic(api_key=api_key)

    def send_message(
        self,
        messages: list[dict],
        tools: list[dict],
        images: list[str],
    ) -> AgentResponse:
        # Convert MCP tool schemas: inputSchema → input_schema
        anthropic_tools = [
            {
                "name": t["name"],
                "description": t.get("description", ""),
                "input_schema": t.get("inputSchema", t.get("input_schema", {})),
            }
            for t in tools
        ]

        # Build message list (copy to avoid mutating caller's list)
        api_messages = [
            {"role": m["role"], "content": m["content"]}
            for m in messages
        ]

        # Inject screenshots into last user message as image content blocks
        if images and api_messages:
            last = api_messages[-1]
            text = last["content"] if isinstance(last["content"], str) else ""
            image_blocks = [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/png",
                        "data": img,
                    },
                }
                for img in images
            ]
            last["content"] = [*image_blocks, {"type": "text", "text": text}]

        response = self._client.messages.create(
            model=self._model,
            max_tokens=4096,
            tools=anthropic_tools,
            messages=api_messages,
        )

        content = ""
        tool_calls: list[dict] = []
        for block in response.content:
            if block.type == "text":
                content = block.text
            elif block.type == "tool_use":
                tool_calls.append({
                    "name": block.name,
                    "input": block.input,
                    "id": block.id,
                })

        return AgentResponse(
            content=content,
            tool_calls=tool_calls,
            stop_reason=response.stop_reason or "end_turn",
        )

    def get_model_name(self) -> str:
        return self._model

    def supports_vision(self) -> bool:
        return True
