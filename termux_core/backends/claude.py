"""Claude backend adapter for Termux core."""

import os

import anthropic

from .base import AgentResponse, BackendAdapter


class ClaudeBackend(BackendAdapter):
    """Anthropic Claude backend."""

    def __init__(self, model: str = "claude-sonnet-4-5", api_key: str = "") -> None:
        self._model = model
        key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        self._client = anthropic.Anthropic(api_key=key)

    def send_message(
        self,
        messages: list[dict],
        tools: list[dict],
        images: list[str],
    ) -> AgentResponse:
        anthropic_tools = [
            {
                "name": t["name"],
                "description": t.get("description", ""),
                "input_schema": t.get("inputSchema", t.get("input_schema", {})),
            }
            for t in tools
        ]

        api_messages = [
            {"role": m["role"], "content": m["content"]}
            for m in messages
        ]

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
