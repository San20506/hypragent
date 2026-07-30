"""Gemini backend adapter for Termux core."""

import os

import google.generativeai as genai

from .base import AgentResponse, BackendAdapter


class GeminiBackend(BackendAdapter):
    """Google Gemini backend."""

    def __init__(self, model: str = "gemini-2.5-flash", api_key: str = "") -> None:
        self._model = model
        key = api_key or os.environ.get("GEMINI_API_KEY", "")
        genai.configure(api_key=key)
        self._client = genai.GenerativeModel(model)

    def send_message(
        self,
        messages: list[dict],
        tools: list[dict],
        images: list[str],
    ) -> AgentResponse:
        # Convert MCP tool schemas to Gemini format
        gemini_tools = [
            {
                "name": t["name"],
                "description": t.get("description", ""),
                "parameters": t.get("inputSchema", {}),
            }
            for t in tools
        ]

        # Build conversation
        chat = self._client.start_chat()
        response = chat.send_message(
            messages[-1]["content"] if messages else "",
            tools=gemini_tools,
        )

        content = ""
        tool_calls: list[dict] = []

        for part in response.parts:
            if hasattr(part, "text"):
                content = part.text
            elif hasattr(part, "function_call"):
                fc = part.function_call
                tool_calls.append({
                    "name": fc.name,
                    "input": dict(fc.args),
                    "id": fc.name,
                })

        return AgentResponse(
            content=content,
            tool_calls=tool_calls,
            stop_reason="end_turn" if not tool_calls else "tool_use",
        )

    def get_model_name(self) -> str:
        return self._model

    def supports_vision(self) -> bool:
        return True
