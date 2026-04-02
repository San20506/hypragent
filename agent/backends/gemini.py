"""Gemini backend adapter — Milestone M11."""

import os

import google.generativeai as genai

from agent.backends.base import AgentResponse, BackendAdapter


class GeminiBackend(BackendAdapter):
    """Google Gemini backend (gemini-2.5-flash default)."""

    def __init__(self, config: dict) -> None:
        self.config = config
        self._model_name: str = config["model"]
        api_key = os.environ[config["api_key_env"]]
        genai.configure(api_key=api_key)
        self._model = genai.GenerativeModel(self._model_name)

    def send_message(
        self,
        messages: list[dict],
        tools: list[dict],
        images: list[str],
    ) -> AgentResponse:
        # Convert tools to Gemini function declarations
        gemini_tools = None
        if tools:
            function_declarations = [
                genai.protos.FunctionDeclaration(
                    name=t["name"],
                    description=t.get("description", ""),
                    parameters=genai.protos.Schema(
                        type=genai.protos.Type.OBJECT,
                        properties={
                            k: genai.protos.Schema(type=genai.protos.Type.STRING)
                            for k in t.get("inputSchema", {}).get("properties", {})
                        },
                    ),
                )
                for t in tools
            ]
            gemini_tools = [genai.protos.Tool(function_declarations=function_declarations)]

        # Build contents list (Gemini uses "contents" not "messages")
        contents = []
        for msg in messages:
            role = "user" if msg["role"] == "user" else "model"
            content = msg["content"]
            if isinstance(content, str):
                contents.append({"role": role, "parts": [{"text": content}]})
            else:
                # Flatten list of blocks to text
                text = " ".join(
                    b.get("text", "") or b.get("content", "")
                    for b in content if isinstance(b, dict)
                )
                contents.append({"role": role, "parts": [{"text": text}]})

        # Inject screenshots into last user content
        if images and contents:
            last = contents[-1]
            for img_b64 in images:
                last["parts"].append({
                    "inline_data": {
                        "mime_type": "image/png",
                        "data": img_b64,
                    }
                })

        response = self._model.generate_content(
            contents,
            tools=gemini_tools,
        )

        content = ""
        tool_calls: list[dict] = []
        for part in response.parts:
            if hasattr(part, "text") and part.text:
                content = part.text
            elif hasattr(part, "function_call") and part.function_call:
                fc = part.function_call
                tool_calls.append({
                    "name": fc.name,
                    "input": dict(fc.args),
                    "id": fc.name,  # Gemini returns no call ID; use name as fallback
                })

        stop_reason = "end_turn" if not tool_calls else "tool_use"
        return AgentResponse(content=content, tool_calls=tool_calls, stop_reason=stop_reason)

    def get_model_name(self) -> str:
        return self._model_name

    def supports_vision(self) -> bool:
        return True
