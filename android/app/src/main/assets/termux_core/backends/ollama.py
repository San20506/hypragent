"""Ollama backend adapter for Termux core."""

import os

import ollama

from .base import AgentResponse, BackendAdapter


class OllamaBackend(BackendAdapter):
    """Ollama local LLM backend."""

    def __init__(self, endpoint: str = "http://localhost:11434", model: str = "llava") -> None:
        self._endpoint = endpoint
        self._model = model
        self._client = ollama.Client(host=endpoint)

    def send_message(
        self,
        messages: list[dict],
        tools: list[dict],
        images: list[str],
    ) -> AgentResponse:
        ollama_messages = [
            {"role": m["role"], "content": m["content"]}
            for m in messages
        ]

        # Add images to the last message if present
        if images and ollama_messages:
            ollama_messages[-1]["images"] = images

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
        ]

        response = self._client.chat(
            model=self._model,
            messages=ollama_messages,
            tools=ollama_tools,
        )

        content = response.get("message", {}).get("content", "")
        tool_calls: list[dict] = []

        for tc in response.get("message", {}).get("tool_calls", []):
            fn = tc.get("function", {})
            tool_calls.append({
                "name": fn.get("name", ""),
                "input": fn.get("arguments", {}),
                "id": fn.get("name", ""),
            })

        return AgentResponse(
            content=content,
            tool_calls=tool_calls,
            stop_reason="end_turn" if not tool_calls else "tool_use",
        )

    def get_model_name(self) -> str:
        return self._model

    def supports_vision(self) -> bool:
        return "llava" in self._model.lower() or "vision" in self._model.lower()
