"""OpenAI-compatible backend adapter.

Works with any OpenAI-compatible API:
  - OpenCode Go   (https://opencode.ai/zen/go/v1)
  - OpenRouter    (https://openrouter.ai/api/v1)
  - OpenAI        (https://api.openai.com/v1)
  - Local vLLM    (http://localhost:8000/v1)
  - Ollama        (http://localhost:11434/v1)
"""

import os

import httpx

from agent.backends.base import AgentResponse, BackendAdapter


class OpenAICompatibleBackend(BackendAdapter):
    """OpenAI-compatible backend — one adapter for many providers."""

    def __init__(self, config: dict) -> None:
        self.config = config
        self._model: str = config["model"]
        self._base_url: str = config.get("base_url", "https://api.openai.com/v1")
        # Strip trailing slash
        self._base_url = self._base_url.rstrip("/")
        api_key = os.environ.get(config["api_key_env"], "")
        if not api_key:
            raise ValueError(
                f"API key not found in env var {config['api_key_env']}. "
                f"Set it via: export {config['api_key_env']}=..."
            )
        self._api_key = api_key
        self._client = httpx.Client(timeout=120.0)

    def send_message(
        self,
        messages: list[dict],
        tools: list[dict],
        images: list[str],
    ) -> AgentResponse:
        # Convert MCP tool schemas: inputSchema → function.parameters
        openai_tools = None
        if tools:
            openai_tools = [
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

        # Build message list
        api_messages = []
        for msg in messages:
            content = msg["content"]
            if isinstance(content, str):
                api_messages.append({"role": msg["role"], "content": content})
            elif isinstance(content, list):
                # Already structured — pass through
                api_messages.append({"role": msg["role"], "content": content})
            else:
                api_messages.append({"role": msg["role"], "content": str(content)})

        # Inject screenshots into the last user message as vision content blocks
        if images and api_messages:
            last = api_messages[-1]
            text = ""
            if isinstance(last["content"], str):
                text = last["content"]
            elif isinstance(last["content"], list):
                text = " ".join(
                    b.get("text", "") or ""
                    for b in last["content"]
                    if isinstance(b, dict) and b.get("type") == "text"
                )
            image_blocks = [
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{img}",
                        "detail": "auto",
                    },
                }
                for img in images
            ]
            last["content"] = [*image_blocks, {"type": "text", "text": text}]

        payload = {
            "model": self._model,
            "messages": api_messages,
        }
        if openai_tools:
            payload["tools"] = openai_tools
            payload["tool_choice"] = "auto"

        response = self._client.post(
            f"{self._base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
        )
        response.raise_for_status()
        data = response.json()

        choice = data["choices"][0]
        msg = choice.get("message", {})
        content = msg.get("content") or ""

        tool_calls: list[dict] = []
        for tc in msg.get("tool_calls", []) or []:
            import json
            func = tc.get("function", {})
            try:
                args = json.loads(func.get("arguments", "{}"))
            except json.JSONDecodeError:
                args = {}
            tool_calls.append({
                "name": func.get("name", ""),
                "input": args,
                "id": tc.get("id", ""),
            })

        stop_reason = choice.get("finish_reason", "stop")
        if stop_reason == "tool_calls":
            stop_reason = "tool_use"

        return AgentResponse(
            content=content,
            tool_calls=tool_calls,
            stop_reason=stop_reason,
        )

    def get_model_name(self) -> str:
        return self._model

    def supports_vision(self) -> bool:
        return True
